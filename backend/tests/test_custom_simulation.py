import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.custom_simulation import CustomDesign, SimulationConfig, CompareSimulationRequest
from services.custom_simulation import run_custom_simulation, validate_simulation_design
from api.custom_simulation import compare


def graph(components, connections, name="Test"):
    return CustomDesign(name=name, components=components, connections=connections)


class CustomSimulationTests(unittest.TestCase):
    def test_routing_and_measured_metrics(self):
        design=graph(
            [{"id":"client","type":"client","name":"Client"},
             {"id":"lb","type":"load_balancer","name":"LB"},
             {"id":"a","type":"application_server","name":"App A"},
             {"id":"b","type":"application_server","name":"App B"},
             {"id":"db","type":"database","name":"DB"}],
            [{"source":"client","target":"lb"},{"source":"lb","target":"a"},
             {"source":"lb","target":"b"},{"source":"a","target":"db"},{"source":"b","target":"db"}])
        result=run_custom_simulation(design,SimulationConfig(duration=3,initial_request_rate=40,seed=3))
        self.assertGreater(result["metrics"]["component_requests"]["a"],0)
        self.assertGreater(result["metrics"]["component_requests"]["b"],0)
        m=result["metrics"]
        self.assertEqual(m["total_incoming"],m["successful"]+m["failed"]+m["dropped"])
        self.assertGreater(m["p99_response_ms"],0)
        self.assertEqual(result["seed"],3)

    def test_contention_and_queue_drops(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"App","config":{"max_concurrent":1,"max_queue_length":0,"processing_latency_ms":100}}],[{"source":"c","target":"app"}])
        result=run_custom_simulation(design,SimulationConfig(duration=1,initial_request_rate=500,seed=1))
        self.assertGreater(result["metrics"]["dropped"],0)
        self.assertGreater(result["metrics"]["component_utilization"]["app"],.75)

    def test_application_concurrency_slot_is_released_after_request(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"App","config":{"max_concurrent":1,"processing_latency_ms":1,"processing_capacity_rps":1000}}],[{"source":"c","target":"app"}])
        result=run_custom_simulation(design,SimulationConfig(duration=5,initial_request_rate=5,seed=14))
        self.assertGreater(result["metrics"]["successful"],5)
        self.assertEqual(result["metrics"]["dropped"],0)

    def test_scheduled_failure_and_recovery(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"App"}],[{"source":"c","target":"app"}])
        config=SimulationConfig(duration=2,initial_request_rate=50,scenario="server_failure",affected_components=["app"],failure_start_time=.3,recovery_time=.4,seed=2)
        result=run_custom_simulation(design,config)
        self.assertTrue(any(event["type"]=="failure" for event in result["events"]))
        self.assertTrue(any(event["type"]=="recovery" for event in result["events"]))
        self.assertGreater(result["metrics"]["failed"],0)

    def test_autoscaling(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"asg","type":"auto_scaling_group","name":"Workers","config":{"instances":1,"min_instances":1,"max_instances":3,"max_concurrent":2,"scale_up_threshold":0.1,"launch_delay":0.05}}],[{"source":"c","target":"asg"}])
        config=SimulationConfig(duration=4,scenario="auto_scaling",initial_request_rate=250,peak_request_rate=400,scaling_cooldown=0,seed=1)
        result=run_custom_simulation(design,config)
        self.assertGreater(result["metrics"]["active_instances"]["asg"],1)
        self.assertTrue(any(event["type"]=="scale_complete" for event in result["events"]))

    def test_cache_short_circuits_database_on_hit(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"cache","type":"cache","name":"Redis","config":{"hit_rate":1}},{"id":"db","type":"database","name":"DB"}],[{"source":"c","target":"cache"},{"source":"cache","target":"db"}])
        result=run_custom_simulation(design,SimulationConfig(duration=2,initial_request_rate=20,seed=4))
        self.assertGreater(result["metrics"]["cache_hits"]["cache"],0)
        self.assertEqual(result["metrics"]["database_requests"],0)

    def test_database_slowdown_and_network_delay(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"App"},{"id":"db","type":"database","name":"DB"}],[{"source":"c","target":"app"},{"source":"app","target":"db"}])
        slow=run_custom_simulation(design,SimulationConfig(duration=2,initial_request_rate=20,scenario="database_slowdown",failure_start_time=0,database_slowdown_duration=1,database_latency_ms=500,seed=12))
        self.assertTrue(any(event["type"]=="database_slowdown" for event in slow["events"]))
        self.assertGreater(slow["metrics"]["database_average_latency_ms"],100)
        normal=run_custom_simulation(design,SimulationConfig(duration=2,initial_request_rate=20,seed=12))
        network=run_custom_simulation(design,SimulationConfig(duration=2,initial_request_rate=20,scenario="network_latency",network_latency_ms=100,seed=12))
        self.assertGreater(network["metrics"]["average_response_ms"],normal["metrics"]["average_response_ms"]+100)

    def test_random_component_failure(self):
        design=graph([{"id":"c","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"Flaky","config":{"failure_probability":1,"recovery_time":.2}}],[{"source":"c","target":"app"}])
        result=run_custom_simulation(design,SimulationConfig(duration=1,initial_request_rate=10,seed=5))
        self.assertGreater(result["metrics"]["failed"],0)
        self.assertTrue(any(event["description"].startswith("random component failure") for event in result["events"]))

    def test_invalid_graph_and_comparison(self):
        cyclic=graph([{"id":"c","type":"client","name":"Client"},{"id":"a","type":"application_server","name":"App"}],[{"source":"c","target":"a"},{"source":"a","target":"c"}])
        with self.assertRaisesRegex(ValueError,"Cyclic"):
            validate_simulation_design(cyclic)
        a=graph([{"id":"c","type":"client","name":"Client"},{"id":"a","type":"application_server","name":"App"}],[{"source":"c","target":"a"}],"A")
        b=graph([{"id":"c","type":"client","name":"Client"},{"id":"cdn","type":"cdn","name":"CDN"},{"id":"a","type":"application_server","name":"App"}],[{"source":"c","target":"cdn"},{"source":"cdn","target":"a"}],"B")
        result=compare(CompareSimulationRequest(designs=[a,b],config=SimulationConfig(duration=1,initial_request_rate=5)))
        self.assertEqual(len(result["comparisons"]),2)
        self.assertIn("SimPy",result["summary"])
        self.assertEqual(result["comparisons"][0]["metrics"]["total_incoming"],result["comparisons"][1]["metrics"]["total_incoming"])

    def test_predefined_strategies_use_independent_graph_adapter(self):
        result=compare(CompareSimulationRequest(designs=[],include_predefined=True,config=SimulationConfig(duration=1,initial_request_rate=3,peak_request_rate=4,max_requests=20)))
        self.assertEqual(len(result["comparisons"]),4)
        self.assertEqual({row["architecture"] for row in result["comparisons"]},{"Single Server","Load Balanced","Auto Scaling","Three Tier"})


if __name__=="__main__":
    unittest.main()

import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.schemas import SimulationRequest
from services.intelligence import analyze_graph, estimate_cost, pdf_report, recommend, explain_simulation, _available_text_models
from api.intelligence import Design, OptimizeRequest, optimization

class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.design=Design(name="test",components=[{"id":"client","type":"client","name":"Client"},{"id":"app","type":"application_server","name":"App"},{"id":"db","type":"database","name":"DB"}],connections=[{"source":"client","target":"app"},{"source":"app","target":"db"}])

    def test_cost_and_graph(self):
        self.assertEqual(estimate_cost(self.design)["monthly"],124.1)
        result=analyze_graph(self.design)
        self.assertEqual(len(result["single_points_of_failure"]),1)
        self.assertEqual(result["reliability_score"],82)

    def test_pdf(self):
        data=pdf_report(self.design,analyze_graph(self.design),estimate_cost(self.design))
        self.assertTrue(data.startswith(b"%PDF"))

    def test_optimizer_creates_separate_version(self):
        updated=optimization(OptimizeRequest(design=self.design,accepted=["add_cache","add_replica"]))["design"]
        self.assertIsNone(updated["id"])
        self.assertNotEqual(updated["name"],self.design.name)
        self.assertFalse(any(c.type=="cache" for c in self.design.components))
        self.assertTrue(any(c["type"]=="cache" for c in updated["components"]))

    def test_predefined_simulation_schema_unchanged(self):
        self.assertEqual(SimulationRequest.model_fields.keys(),{"architecture","scenario"})

    def test_gemini_mock_response_and_missing_key(self):
        payload={"name":"Mock design","components":[{"id":"client","type":"client","name":"Client","config":{}}],"connections":[],"explanation":"Mocked","tradeoffs":[],"bottlenecks":[],"scalability":[],"assumptions":[]}
        response=MagicMock(text=__import__("json").dumps(payload)); client=MagicMock(); client.models.generate_content.return_value=response
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test-key","GEMINI_MODEL":"gemini-3.0-flash"}), patch("google.genai.Client",return_value=client):
            self.assertEqual(recommend("simple app")["name"],"Mock design")
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaisesRegex(RuntimeError,"not configured"): recommend("simple app")

    def test_simulation_analysis_uses_mocked_gemini(self):
        response=MagicMock(text="The sampled app utilization indicates the likely bottleneck.")
        client=MagicMock(); client.models.generate_content.return_value=response
        with patch.dict("os.environ",{"GEMINI_API_KEY":"test-key","GEMINI_MODEL":"gemini-3.0-flash"}), patch("google.genai.Client",return_value=client):
            text=explain_simulation(self.design, __import__("models.custom_simulation",fromlist=["SimulationConfig"]).SimulationConfig(duration=1), {"metrics":{"throughput_rps":1},"events":[],"timeline":[]})
        self.assertIn("likely bottleneck",text)
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"],"gemini-3.0-flash")

    def test_model_discovery_prefers_gemini_3_and_filters_non_text_models(self):
        client=MagicMock()
        client.models.list.return_value=[
            MagicMock(name="models/gemini-3.0-flash",supported_actions=["generateContent"]),
            MagicMock(name="models/gemini-3.5-flash-lite",supported_actions=["generateContent"]),
            MagicMock(name="models/gemini-3.0-flash-image",supported_actions=["generateContent"]),
            MagicMock(name="models/gemini-2.5-flash",supported_actions=["generateContent"]),
        ]
        # MagicMock(name=...) names the mock object; set the API model fields explicitly.
        for item,name in zip(client.models.list.return_value,["models/gemini-3.0-flash","models/gemini-3.5-flash-lite","models/gemini-3.0-flash-image","models/gemini-2.5-flash"]):
            item.name=name
        self.assertEqual(_available_text_models(client),["gemini-3.0-flash","gemini-3.5-flash-lite"])

if __name__=="__main__": unittest.main()

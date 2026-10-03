"""Opt-in fictional catalog and scripted test adapter, not the Harry/CS3 implementation."""
from .schemas import Catalog, Interpretation


class DemoCatalog:
    def __init__(self, *, natural_language=False):
        self.natural_language = natural_language

    def load(self) -> Catalog:
        catalog = Catalog.model_validate({
            "version": "fictional-demo-v1", "financeApproved": False, "demo": True,
            "questions": [
                {
                    "id": "attitude", "label": "Fictional attitude to risk",
                    "prompt": "For this fictional demo, type 'some_fluctuation' or 'less_fluctuation'.",
                    "clarification": "Choose 'some_fluctuation' or 'less_fluctuation' for this fictional example.",
                    "options": [
                        {"id": "some_fluctuation", "answer": "In this fictional example, I can handle some ups and downs."},
                        {"id": "less_fluctuation", "answer": "In this fictional example, I prefer fewer ups and downs."},
                    ],
                },
                {
                    "id": "horizon", "label": "Fictional time horizon",
                    "prompt": "For this fictional demo, type 'five_plus' or 'within_three'.",
                    "clarification": "Choose 'five_plus' or 'within_three' for this fictional example.",
                    "options": [
                        {"id": "five_plus", "answer": "In this fictional example, I will not need the money for at least five years."},
                        {"id": "within_three", "answer": "In this fictional example, I might need the money within three years."},
                    ],
                },
                {
                    "id": "capacity", "label": "Fictional capacity for loss",
                    "prompt": "For this fictional demo, type 'essentials_covered' or 'essentials_affected'.",
                    "clarification": "Choose 'essentials_covered' or 'essentials_affected' for this fictional example.",
                    "requiresExplicitConfirmation": True,
                    "options": [
                        {"id": "essentials_covered", "answer": "In this fictional example, a loss would not affect essential spending."},
                        {"id": "essentials_affected", "answer": "In this fictional example, a loss could affect essential spending."},
                    ],
                },
            ],
        })
        if self.natural_language:
            catalog.version = "fictional-language-demo-v1"
            prompts = {
                "attitude": "For a fictional investment, how would you feel about its value going up and down?",
                "horizon": "For this fictional example, when might you need the money?",
                "capacity": "For this fictional example, could you cover essential spending if the investment lost value?",
            }
            for question in catalog.questions:
                question.prompt = prompts[question.id]
                question.clarification = "Please clarify which fictional answer fits: " + " Or: ".join(
                    option.answer for option in question.options
                )
        return catalog


class ScriptedDemoAdapter:
    def interpret(self, *, text, question, catalog, confirmed_answers, context) -> Interpretation:
        # An exact option-ID selection exercises orchestration without pretending to interpret prose.
        option_id = text.strip().lower()
        if any(option.id == option_id for option in question.options):
            return Interpretation(kind="proposal", optionId=option_id)
        return Interpretation(kind="clarification")

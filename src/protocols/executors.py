from src.llm.models import LLMJobInput, CandidateProfile, LLMRuntimeConfig
from typing import Protocol

class LLMExecutorProtocol(Protocol):
    def execute(
        self,
        job_inputs: list[LLMJobInput],
        candidate_profile: CandidateProfile,
        runtime_config: LLMRuntimeConfig,
    ) -> None:
        ...
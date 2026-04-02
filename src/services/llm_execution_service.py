from src.llm.models import LLMPreparedInputsResult, LLMRuntimeConfig
from src.llm.standard_executor import StandardLLMExecutor


class LLMExecutionService:
    def __init__(
        self,
        standard_executor: StandardLLMExecutor,
    ) -> None:
        self.standard_executor = standard_executor

    def execute_prepared_inputs(
        self,
        prepared_inputs: LLMPreparedInputsResult,
        runtime_config: LLMRuntimeConfig,
    ) -> None:
        if runtime_config.execution_mode != "standard":
            raise ValueError(
                f"Unsupported execution mode for this service version: {runtime_config.execution_mode}"
            )

        for job_input in prepared_inputs.jobs_to_process:
            self.standard_executor.execute_one(
                job_input=job_input,
                runtime_config=runtime_config,
            )
from agents import (
    Agent, 
    set_default_openai_client,
    RunContextWrapper, 
    GuardrailFunctionOutput,
    TResponseInputItem, 
    input_guardrail, 
    set_tracing_disabled, 
    Runner,
    ModelSettings,
)
from openai import AsyncOpenAI
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.mcp import MCPServerSse
import os
from pydantic import BaseModel
from api.prompts import GUARDRAIL_INSTRUCTIONS, CODING_TUTOR_INSTRUCTIONS

set_tracing_disabled(True)

openrouter_api_key = os.getenv("OPEN_ROUTER_API_KEY")
openrouter_base_url = os.getenv("OPEN_ROUTER_BASE_URL")
openrouter_model = os.getenv("OPEN_ROUTER_MODEL")

client = AsyncOpenAI(
    api_key=openrouter_api_key,
    base_url=openrouter_base_url,
)

set_default_openai_client(client)

def make_model(model_name: str) -> OpenAIChatCompletionsModel:
    return OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=client,
    )

class GuardrailOutput(BaseModel):
    is_allowed: bool
    reasoning: str

guardrail_agent = Agent(
    name="GuardrailAgent",
    instructions=GUARDRAIL_INSTRUCTIONS,
    model=make_model(openrouter_model),
    output_type=GuardrailOutput,
)

@input_guardrail
async def guardrail( 
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output.reasoning, 
        tripwire_triggered=(not result.final_output.is_allowed),
    )

mcp_url = os.getenv("MCP_SERVER_URL")

server = MCPServerSse(
    name="RCE_Code_Editor_Assistant_Tools",
    params={"url": mcp_url},
    cache_tools_list=True,
)

agent = Agent(
    name="CodingTutor",
    instructions=CODING_TUTOR_INSTRUCTIONS,
    model=make_model(openrouter_model),
    model_settings=ModelSettings(parallel_tool_calls=False),
    input_guardrails=[guardrail],
    mcp_servers=[server]
)
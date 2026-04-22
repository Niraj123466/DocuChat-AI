from settings import ORGANIZATION_NAME
def create_query_agent(
    model="gemini-2.0-flash",
    temperature=0.1,
    api_key=None,
    prompt_path="src/utils/prompts.yml"
):
    from langchain_google_genai import ChatGoogleGenerativeAI
    from src.tools.query_tool import get_context
    from src.utils.yaml_loader import load_prompts

    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=api_key,
    )
    prompts = load_prompts(prompt_path)
    system_text = prompts["query_agent_prompt"].format(organization_name=ORGANIZATION_NAME)

    class SimpleExecutor:
        def __init__(self, llm, system_text):
            self.llm = llm
            self.system_text = system_text

        def invoke(self, inputs):
            user_input = inputs.get("input", "")
            try:
                context = get_context.run(user_input)
            except Exception:
                context = ""
            messages = [
                ("system", self.system_text),
                ("human", f"Question:\n{user_input}\n\nContext:\n{context}")
            ]
            resp = self.llm.invoke(messages)
            return {"output": getattr(resp, "content", str(resp))}

    return SimpleExecutor(llm, system_text)

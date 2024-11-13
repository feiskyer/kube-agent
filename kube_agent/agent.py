# -*- coding: utf-8 -*-
import os
import openai
from kube_agent.swarm import Agent, Swarm
from kube_agent.shell import ScriptExecutor
from kube_agent.swarm.repl import process_and_print_streaming_response


def get_llm(model: str, api_key: str = "", api_type: str = "", base_url: str = "", api_version="2024-10-21"):
    '''Get the client from LLM model config.'''
    if api_type == "azure" or os.getenv("OPENAI_API_TYPE") == "azure" or os.getenv("AZURE_OPENAI_API_KEY") != "":
        return openai.AzureOpenAI(
            azure_deployment=model,
            timeout=60,
            api_version=api_version,
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=base_url or os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

    return openai.OpenAI(
        timeout=60,
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
        base_url=base_url or os.getenv("OPENAI_API_BASE"),
    )


def python_executor(script: str) -> str:
    '''Execute the python script.'''
    return ScriptExecutor('python3').run(script, timeout=60)

def shell_executor(script: str) -> str:
    '''Execute the shell script.'''
    return ScriptExecutor("bash").run(script, timeout=60)


class AssistantAgent:
    '''Naive Assistant Agent.'''

    def __init__(self, model: str, api_key: str = "", api_type: str = "", base_url: str = "",
                 api_version="2024-10-21", silent=False):
        '''Initialize the Swarm client and agents.'''
        self.llm = get_llm(model, api_key, api_type, base_url, api_version)
        self.swarm = Swarm(client=self.llm)
        self.model = model
        self.silent = silent

    def run(self, system_prompt: str, prompt: str):
        '''Run the Assistant Agent'''
        agent = Agent(
            name="AssistantAgent",
            model=self.model,
            instructions=system_prompt,
        )
        messages = [{"role": "user", "content": prompt}]
        if self.silent:
            response = self.swarm.run(
                agent=agent,
                messages=messages,
                max_turns=50,
                execute_tools=True,
            )
        else:
            response = self.swarm.run(
                agent=agent,
                messages=messages,
                max_turns=50,
                stream=True,
                execute_tools=True,
            )
            response = process_and_print_streaming_response(response)
        return response.messages[-1]["content"]


class KubeCopilotAgent:
    '''Kubernetes Copilot Agent using Swarm framework.'''

    def __init__(self, model: str, api_key: str = "", api_type: str = "", base_url: str = "",
                 api_version="2024-10-21", silent=False):
        '''Initialize the Swarm client and agents.'''
        self.llm = get_llm(model, api_key, api_type, base_url, api_version)
        self.swarm = Swarm(client=self.llm)
        self.model = model
        self.silent = silent
        self.admin_agent = self.get_admin_agent()
        self.planner_agent = self.get_planner_agent()
        self.critic_agent = self.get_critic_agent()
        self.engineer_agent = self.get_engineer_agent()

    def transfer_to_critic(self):
        '''Transfer to the critic agent.'''
        return self.critic_agent

    def transfer_to_admin(self):
        '''Transfer to the admin agent.'''
        return self.admin_agent

    def transfer_to_planner(self):
        '''Transfer to the planner agent.'''
        return self.planner_agent

    def transfer_to_engineer(self):
        '''Transfer to the engineer agent.'''
        return self.engineer_agent

    def get_planner_agent(self) -> Agent:
        '''Get the planner agent for the Kubernetes Copilot.'''
        return Agent(
            name="Planner",
            model=self.model,
            tool_choice="auto",
            functions=[self.transfer_to_critic, self.transfer_to_admin],
            instructions='''You're a cloud native principal product manager.
            Your task is to devise a comprehensive plan to resolve users' questions related to Kubernetes, ensuring its iterative refinement until approved by critic.

            ## Steps
            1. Draft initial plan with sequential steps for resolving questions. Ensure codes are put in code blocks ```python or ```sh whenever codes are required. DO NOT USE INLINE CODE.
            2. Call critic to review and approve the plan by using transfer_to_critic tool.
            3. Revise plan iteratively based on review feedbacks until it gets approval from critic.
            4. Call admin to execute the approved plan using transfer_to_admin tool.
''')

    def get_critic_agent(self) -> Agent:
        '''Get the critic agent for the Kubernetes Copilot.'''
        return Agent(
            name="Critic",
            model=self.model,
            tool_choice="auto",
            functions=[self.transfer_to_admin, self.transfer_to_planner],
            instructions='''You are an expert and critic in cloud-native technologies and Kubernetes.
            Your task is to evaluate submissions related to cloud-native technologies and Kubernetes, offering detailed, constructive feedback focused on accuracy, feasibility, and inclusion of verifiable information.

            ## Steps
            1. Review submissions: evaluate plans, claims, and codes for accuracy and practicality
            2. Provide feedback:
            - Offer detailed feedback focusing on improving submission quality.
            - For any codes, ensure scripts are complete and ready for execution within code blocks.
            - For inline codes, always suggest converting to code blocks within ```python or ```sh.
            3. Respond feedback and approval:
            - If changes are needed: call planner to improve the submission by transfer_to_planner cool.
            - If submission is approved: call admin to execute the plan by transfer_to_admin tool.
            - If unsure: call admin to make final decisions by transfer_to_admin tool.
''')

    def admin_instructions(self, context_variables):
        '''Get the admin instructions for the Kubernetes Copilot.'''
        original_question = context_variables.get("original_question", "")
        return f'''You're a technical expert specializing in Kubernetes and cloud-native technologies.
        Your task is to help user to resolve their problems in Kubernetes cluster.
        Engage in discussion with planner to develop solution plans and call engineer to execute the codes.
        Call the transfer_to_planner tool

        ## Steps
        1. Call planner to develop solution plans using transfer_to_planner tool.
        2. Once plan gets approved, call engineer to execute the plan scripts using transfer_to_engineer tool.
        3. Repeat steps 1-2 until you can the final answer to user's original question.
        4. Respond with a concise answer to user's original question with 'TERMINATE' at the end.

        ## Original Question
        {original_question}
        '''

    def get_admin_agent(self) -> Agent:
        '''Get the admin agent for the Kubernetes Copilot.'''
        return Agent(
            name="Admin",
            model=self.model,
            tool_choice="auto",
            functions=[self.transfer_to_planner, self.transfer_to_engineer],
            instructions=self.admin_instructions,
            )

    def get_engineer_agent(self) -> Agent:
        '''Get the engineer agent for the Kubernetes Copilot.'''
        return Agent(
            name="Engineer",
            model=self.model,
            tool_choice="auto",
            functions=[python_executor, shell_executor, self.transfer_to_admin],
            instructions='''You're a cloud native principal engineer with access to python_executor and shell_executor tools.
            Your task is to execute the instruction scripts to accomplish the Kubernetes tasks.

            # Steps
            1. Extract the Python/shell scripts.
            2. Execute scripts by calling python_executor or shell_executor tools.
            3. Respond the results via calling transfer_to_admin tool.
''')

    def run(self, instructions: str):
        '''Run the Kubernetes Copilot Agent with Swarm framework.'''
        context_variables = {"original_question": instructions}
        messages = [{"role": "user", "content": instructions}]
        agent = self.admin_agent
        while True:
            if self.silent:
                response = self.swarm.run(
                    agent=agent,
                    messages=messages,
                    max_turns=50,
                    execute_tools=True,
                    context_variables=context_variables,
                )
            else:
                response = self.swarm.run(
                    agent=agent,
                    messages=messages,
                    max_turns=50,
                    stream=True,
                    execute_tools=True,
                    context_variables=context_variables,
                )
                response = process_and_print_streaming_response(response)

            if 'TERMINATE' in response.messages[-1]["content"]:
                return response.messages[-1]["content"].replace('TERMINATE', '')

            messages.extend(response.messages)
            agent = response.agent

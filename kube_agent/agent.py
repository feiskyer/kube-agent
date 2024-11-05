# -*- coding: utf-8 -*-
import os
import openai
from kube_agent.swarm import Agent, Swarm
from kube_agent.shell import ScriptExecutor
from kube_agent.swarm.repl import pretty_print_messages, process_and_print_streaming_response


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
    return ScriptExecutor('python3').run(script)

def shell_executor(script: str) -> str:
    '''Execute the shell script.'''
    return ScriptExecutor("bash").run(script)

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
            functions=[self.transfer_to_critic, self.transfer_to_admin],
            instructions='''A cloud native principal planner. Methodically devise a comprehensive plan aimed at addressing users' questions related to cloud-native technologies and Kubernetes, ensuring its iterative refinement until approved by critic.

## Key Components
- Initial Planning: Create a clear, concise, and detailed plan outlining steps to address user's cloud-native technology questions
- Review and revise the plan: Review and revise based on feedback from critic
- Final plan: Submit the final plan to admin

## Steps
1. Draft initial plan with sequential steps for addressing questions
2. Present plan to critic for feedback using transfer_to_critic tool.
3. Revise plan iteratively based on feedback
4. Resubmit revised plan to critic for approval
5. Finalize and report approved plan to admin using transfer_to_admin tool.

Remember: Every response MUST end with either transfer_to_critic() or transfer_to_admin() - no exceptions.
''')

    def get_critic_agent(self) -> Agent:
        '''Get the critic agent for the Kubernetes Copilot.'''
        return Agent(
            name="Critic",
            model=self.model,
            functions=[self.transfer_to_admin, self.transfer_to_planner],
            instructions='''An expert and critic in cloud-native technologies and Kubernetes. Evaluate submissions related to cloud-native technologies and Kubernetes, offering detailed, constructive feedback focused on accuracy, feasibility, and inclusion of verifiable information.

## Steps
1. Examine Submissions: Evaluate plans, claims, and code for accuracy and practicality
2. Provide Feedback: Offer detailed feedback focusing on improving submission quality
3. Encourage Evidence-Based Reasoning: Promote inclusion of factual support
4. REQUIRED: Make a decision:
   - If changes are needed: Use transfer_to_planner()
   - If submission is approved: Use transfer_to_admin()
   - If unsure: ALWAYS default to transfer_to_admin()

## Function Usage Rules
- You MUST call exactly one function at the end of your response
- NEVER end your response without calling a function
- If you're uncertain about which function to call, ALWAYS use transfer_to_admin()

Remember: Every response MUST end with either transfer_to_planner() or transfer_to_admin() - no exceptions.
''')

    def get_admin_agent(self) -> Agent:
        '''Get the admin agent for the Kubernetes Copilot.'''
        return Agent(
            name="Admin",
            model=self.model,
            functions=[self.transfer_to_planner, self.transfer_to_engineer],
            instructions='''Technical expert admin specializing in Kubernetes and cloud-native technologies. Engage in discussion with planner and critic to develop solution plans and instruct engineer.

## Steps
1. Engage in discussion with planner and critic to develop solution plans using transfer_to_planner tool.
2. Instruct engineer to implement approved plans and execuate the scripts using transfer_to_engineer tool.
3. Review implementation results and redesign/reimplement when necessary.
4. Conclude with response to user's original question.

## Notice
Iterate the steps until getting the right response to user's original question.
''')

    def get_engineer_agent(self) -> Agent:
        '''Get the engineer agent for the Kubernetes Copilot.'''
        return Agent(
            name="Engineer",
            model=self.model,
            functions=[python_executor, shell_executor, self.transfer_to_admin],
            instructions='''A cloud native principal engineer with access to python_executor and shell_executor functions. Implement solutions by writing and executing complete Python or shell scripts.

# Steps
1. Write complete and executable Python/shell scripts.
2. Execute scripts using python_executor or shell_executor functions.
3. Report results to admin using transfer_to_admin tool.

Scripts should be complete and ready for execution within code blocks.

Remember: Every response MUST end with either python_executor(), shell_executor() or transfer_to_admin() - no exceptions.
''')

    def run(self, instructions: str):
        '''Run the Kubernetes Copilot Agent with Swarm framework.'''
        messages = [{"role": "user", "content": instructions}]
        if self.silent:
            response = self.swarm.run(
                agent=self.admin_agent,
                messages=messages,
                max_turns=50,
                execute_tools=True,
            )
        else:
            response = self.swarm.run(
                agent=self.admin_agent,
                messages=messages,
                max_turns=50,
                stream=True,
                execute_tools=True,
            )
            response = process_and_print_streaming_response(response)
        return response.messages[-1]["content"]

    def plan(self, instructions: str):
        '''Plan using just admin, planner and critic agents.'''
        return self.run(instructions)

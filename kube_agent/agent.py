# -*- coding: utf-8 -*-
import os
import autogen
from autogen import AssistantAgent

AZURE_OAI_API_VERSION = "2024-02-01"


def get_llm_config(model: str, api_key: str = "", api_type: str = "", base_url: str = "", api_version: str = ""):
    '''Get the configuration for the LLM model.'''
    config = {
        "model": model,
        "api_key": api_key,
    }
    if api_key:
        config["api_key"] = api_key
    elif os.getenv("OPENAI_API_KEY"):
        config["api_key"] = os.getenv("OPENAI_API_KEY")
    elif os.getenv("AZURE_OPENAI_API_KEY"):
        config["api_key"] = os.getenv("AZURE_OPENAI_API_KEY")
    else:
        raise ValueError("OpenAI API key is required.")

    if api_type:
        config["api_type"] = api_type
    elif os.getenv("AZURE_OPENAI_API_KEY") or (os.getenv("OPENAI_API_BASE") is not None and "azure" in os.getenv("OPENAI_API_BASE")):
        config["api_type"] = "azure"
    elif os.getenv("OPENAI_API_TYPE"):
        config["api_type"] = os.getenv("OPENAI_API_TYPE")

    if api_version:
        config["api_version"] = api_version
    elif config["api_type"] == "azure":
        config["api_version"] = AZURE_OAI_API_VERSION

    if base_url:
        config["base_url"] = base_url
    elif os.getenv("OPENAI_API_BASE"):
        config["base_url"] = os.getenv("OPENAI_API_BASE")
    elif os.getenv("AZURE_OPENAI_ENDPOINT"):
        config["base_url"] = os.getenv("AZURE_OPENAI_ENDPOINT")

    return {
        "timeout": 60,
        "cache_seed": 42,
        "config_list": [config],
        "temperature": 0,
    }


class KubeCopilotAgent:
    '''Kubernetes Copilot Agent.'''

    def __init__(self, model: str, api_key: str = "", api_type: str = "", base_url: str = "", api_version: str = "", silent=False):
        '''Initialize the LLM chain.'''
        self.silent = silent
        self.llm_config = get_llm_config(
            model, api_key, api_type, base_url, api_version)
        self.admin = self.get_admin()
        self.plan_manager = self.get_plan_manager()
        self.execute_manager = self.get_execute_manager()

    def termination_msg(self, x):
        '''Check if the message is a termination message.'''
        return isinstance(x, dict) and ("TERMINATE" == str(x.get("content", "")).strip()[-9:].upper() or
                                        "TERMINATE." == str(x.get("content", "")).strip()[-10:].upper())

    def get_admin(self):
        '''Get the admin for the Kubernetes Copilot.'''
        return autogen.UserProxyAgent(
            name="Admin",
            human_input_mode="NEVER",
            llm_config=self.llm_config,
            system_message='''A technical expert administrator in Kubernetes and cloud-native technologies. Interact with the planner to discuss and develop a comprehensive plan to resolve users' cloud-native questions. The execution of this plan must receive your approval before implementation. Ensure that your discussion covers all necessary technical considerations and that the plan is feasible, efficient, and aligns with best practices in cloud-native technologies. Response TERMINATE at the end when all done.''',
            is_termination_msg=self.termination_msg,
            code_execution_config=False,
        )

    def get_plan_manager(self):
        '''Get the plan manager for the Kubernetes Copilot.'''
        planner = autogen.AssistantAgent(
            name="Planner",
            is_termination_msg=self.termination_msg,
            system_message='''A cloud native principal planner, responsible to methodically devise a comprehensive plan aimed at resolving users' questions related to cloud-native technologies and Kubernetes. Your approach should include iterative revisions of the plan based on feedback from both the administrative and critical review teams until you receive final approval from the admin.

        # Guidelines

        1. Begin by clearly explaining the proposed plan, ensuring to delineate the specific steps and their sequential order.
        2. Specify the roles and responsibilities within the plan, clearly indicating which steps will be executed by the engineer, including any code writing tasks, and which steps require the admin to procure additional troubleshooting guides related to Kubernetes.
        3. Incorporate a mechanism for receiving and integrating feedback from the admin and critic into the plan. This includes being open to revisions and adjustments to ensure the plan meets all technical and practical requirements for approval.
        4. Aim for clarity and precision in your plan to ensure that the roles of each participant are distinctly understood, facilitating a smooth execution process.
        ''',
            llm_config=self.llm_config,
        )
        critic = autogen.AssistantAgent(
            name="Critic",
            system_message='''An expert and critic in cloud-native technologies and Kubernetes, responsible to meticulously evaluate plans, claims, and code submitted by other agents in a step-by-step manner. Provide constructive feedback on their submissions, with a particular focus on the inclusion of verifiable information and the overall validity and feasibility of the proposed solutions.

        # Guidelines

        1. Examine each element of the submissions (plans, claims, code) for accuracy, practicality, and adherence to best practices in cloud-native and Kubernetes environments.
        2. Ensure that the plans include verifiable information, such as data sources, benchmarks, and references, to support the proposed solutions and claims.
        3. Assess the code for correctness, efficiency, and alignment with the outlined plan. Verify that it is complete, executable, and appropriately addresses the task at hand.
        4. Provide detailed feedback aimed at improving the quality and effectiveness of the submissions. Highlight areas of strength as well as suggest modifications for any identified issues or gaps.
        5. Encourage the incorporation of evidence-based reasoning and factual support in the plans and claims to enhance their credibility and reliability.
        ''',
            is_termination_msg=self.termination_msg,
            llm_config=self.llm_config,
        )
        plan_groupchat = autogen.GroupChat(
            messages=[],
            agents=[self.admin, planner, critic],
            send_introductions=True,
            max_round=30)
        return autogen.GroupChatManager(
            name='plan_manager',
            groupchat=plan_groupchat,
            llm_config=self.llm_config)

    def get_execute_manager(self):
        '''Get the execute manager for the Kubernetes Copilot.'''
        engineer = AssistantAgent(
            name="Engineer",
            is_termination_msg=self.termination_msg,
            system_message='''A cloud native principal engineer, tasked with implementing solutions for cloud-native technologies using an approved plan. Responsible for writing complete and executable Python or shell scripts to accomplish various tasks. Ensure the code is encapsulated within a code block, clearly specifying the script type (Python or Shell). The code must be designed to be used as is, without requiring any modifications by the user.''',
            llm_config=self.llm_config,
        )
        executor = autogen.UserProxyAgent(
            name="Executor",
            system_message="Executor. Execute the code written by the engineer and report the result.",
            human_input_mode="NEVER",
            code_execution_config={
                "last_n_messages": 3,
                "work_dir": ".work",
                "use_docker": False,
            },
            is_termination_msg=self.termination_msg,
        )
        execute_groupchat = autogen.GroupChat(
            messages=[],
            agents=[self.admin, engineer, executor],
            send_introductions=True,
            max_round=30)
        return autogen.GroupChatManager(
            name='execute_manager',
            groupchat=execute_groupchat,
            llm_config=self.llm_config)

    def plan(self, instructions):
        '''Plan the Kubernetes Copilot Agent. This is useful when code execution is not required.'''
        plan = self.admin.initiate_chat(
            self.plan_manager,
            message=instructions,
            clear_history=False,
            silent=self.silent,
            summary_method="reflection_with_llm",
            summary_args={
                "summary_prompt": "Layout the plan that was approved by the critic",
            }
        )
        return plan.summary

    def run(self, instructions):
        '''Run the Kubernetes Copilot Agent.'''
        plan = self.admin.initiate_chat(
            self.plan_manager,
            message=instructions,
            clear_history=False,
            silent=self.silent,
            summary_method="reflection_with_llm",
            summary_args={
                "summary_prompt": "Layout the plan that was approved by the critic",
            }
        )
        result = self.admin.initiate_chat(
            self.execute_manager,
            message=plan.summary,
            clear_history=False,
            silent=self.silent,
            summary_method="reflection_with_llm",
            summary_args={
                "summary_prompt": "Layout the execution result in details according to the planner's instructions",
            }
        )
        return result.summary

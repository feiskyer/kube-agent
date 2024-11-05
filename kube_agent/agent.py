# -*- coding: utf-8 -*-
import os

from autogen_agentchat.agents import (AssistantAgent, CodeExecutorAgent)
from autogen_agentchat.task import TextMentionTermination
from autogen_agentchat.teams import Swarm
from autogen_core.components.code_executor import (
    LocalCommandLineCodeExecutor)
from autogen_ext.models import (AzureOpenAIChatCompletionClient,
                                OpenAIChatCompletionClient)


def get_llm(model: str, api_key: str = "", api_type: str = "", base_url: str = "", api_version="2024-10-21"):
    '''Get the client from LLM model config.'''
    if api_type == "azure" or os.getenv("OPENAI_API_TYPE") == "azure" or os.getenv("AZURE_OPENAI_API_KEY") != "":
        return AzureOpenAIChatCompletionClient(
            model=model,
            azure_deployment=model,
            timeout=60,
            temperature=0,
            api_version=api_version,
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=base_url or os.getenv("AZURE_OPENAI_ENDPOINT"),
            model_capabilities={
                "vision": True,
                "function_calling": True,
                "json_output": True,
            },
        )

    return OpenAIChatCompletionClient(
        model=model,
        timeout=60,
        temperature=0,
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
        base_url=base_url or os.getenv("OPENAI_API_BASE"),
    )


async def local_executor(script: str):
    '''Execute the script code and report the result.'''
    code_executor = LocalCommandLineCodeExecutor()
    executor = CodeExecutorAgent(
        name="CodeExecutor",
        code_executor=code_executor,
        description="Execute the code written by the engineer and report the result.",
    )
    result = await executor.run(script)
    return result.messages[-1].content


class KubeCopilotAgent:
    '''Kubernetes Copilot Agent.'''

    def __init__(self, model: str, api_key: str = "", api_type: str = "", base_url: str = "", api_version="2024-10-21", silent=False):
        '''Initialize the LLM chain.'''
        self.silent = silent
        self.llm = get_llm(model, api_key, api_type, base_url, api_version)

    def termination_msg(self, x):
        '''Check if the message is a termination message.'''
        if not isinstance(x, dict):
            return False

        if not x.get("content", ""):
            return False

        content = str(x.get("content", "")).strip()
        content = content.rstrip(".").rstrip("*").strip()
        return "TERMINATE" == content[-9:].upper()


    def get_planner_agent(self):
        '''Get the planner agent for the Kubernetes Copilot.'''
        return AssistantAgent(
            name="Planner",
            model_client=self.llm,
            handoffs=["Critic", "Admin"],
            description="A cloud native principal planner, responsible to methodically devise a comprehensive plan aimed at resolving users' questions related to cloud-native technologies and Kubernetes.",
            system_message='''A cloud native principal planner. Methodically devise a comprehensive plan aimed at addressing users' questions related to cloud-native technologies and Kubernetes, ensuring its iterative refinement until approved by critic.

## Key Components

- **Initial Planning:** Create a clear, concise, and detailed plan outlining the steps necessary to address user's cloud-native technology questions, specifically relating to Kubernetes.
- **Review and revise the plan**: Review and revise the plan iteratively based on feedback from critic.
- **Final plan**: Submit the final plan to admin.

## Steps

1. Draft the initial plan with sequential steps for addressing the questions.
2. Present the plan to the critic for feedback.
3. Revise the plan iteratively based on feedback.
4. Resubmit the revised plan to critic for approval.
5. Finalize and report the approved plan to admin.
''',
        )

    def get_critic_agent(self):
        '''Get the critic agent for the Kubernetes Copilot.'''
        return AssistantAgent(
            name="Critic",
            model_client=self.llm,
            handoffs=["Admin", "Planner"],
            description="An expert and critic in cloud-native technologies and Kubernetes, responsible to meticulously evaluate plans, claims, and code submitted by other agents in a step-by-step manner.",
            system_message='''An expert and critic in cloud-native technologies and Kubernetes. Evaluate submissions related to cloud-native technologies and Kubernetes, offering detailed, constructive feedback focused on accuracy, feasibility, and inclusion of verifiable information.

- Assess each submission element (plans, claims, code) with respect to cloud-native and Kubernetes best practices.
- Check for the presence of verifiable information like data sources, benchmarks, and references in the plans.
- Evaluate the code for correctness, efficiency, and its execution according to the plan, ensuring completeness and task relevance.
- Provide feedback aimed at improving quality and effectiveness, highlighting strengths and offering constructive suggestions for improvement.

# Steps

1. **Examine Submissions:** Evaluate plans, claims, and code for accuracy, practicality, and adherence to best cloud-native practices.
   - For plans: Check for data sources, benchmarks, and references.
   - For claims: Verify factual accuracy and logical consistency.
   - For code: Assess correctness, completeness, and adherence to the initial plan.
2. **Provide Feedback:** Offer detailed feedback focusing on improving submission quality.
   - Highlight strong areas.
   - Suggest modifications for identified issues or gaps.
3. **Encourage Evidence-Based Reasoning:** Promote the inclusion of factual support to strengthen the credibility of claims.

# Output Format

Provide feedback in a detailed paragraph format, with separate sections for evaluation findings and suggested improvements.
''',
        )

    def get_admin_agent(self):
        '''Get the admin agent for the Kubernetes Copilot.'''
        return AssistantAgent(
            name="Admin",
            model_client=self.llm,
            handoffs=["Planner", "Engineer"],
            system_message='''Assume the role of a technical expert admin specializing in Kubernetes and cloud-native technologies. Your task is to engage in a discussion with planner and critic to develop a comprehensive solution plan and instruct engineer to implement the plan to address users' cloud-native questions.
# Steps

1. Engage in a discussion with planner and critic to develop a comprehensive solution plan.
2. Review the plan for technical correctness, feasibility, and alignment with cloud-native best practices.
3. Instruct engineer to implement the plan.
4. Review the implementation result.
5. Conclude your participations and respond to the user's original question.
6. Ends with the word 'TERMINATE' once done all the discussions.
''',
        )

      

    def get_engineer_agent(self):
        '''Get the engineer agent for the Kubernetes Copilot.'''
        return AssistantAgent(
            name="Engineer",
            model_client=self.llm,
            tools=[local_executor],
            handoffs=["Admin"],
            description="A cloud native principal engineer, tasked with implementing solutions for cloud-native technologies using an approved plan.",
            system_message='''A cloud native principal engineer with access to the local_executor tool. 
            Implement solutions for cloud-native technologies by writing and executing complete and executable Python or shell scripts.

# Steps

1. **Understand the Task**: Examine the requirements of the approved plan to determine the specific functionality or operations required.
2. **Choose the Script Type**: Decide whether a Python or shell script is more suitable for the task based on the capabilities needed and implementation plan.
3. **Write the Script with the appropriate language**:
   - For Python scripts: focus on clarity and efficiency, utilizing built-in functions and libraries as needed.
   - For Shell scripts: ensure compatibility with common shell environments, using standard command-line tools.
4. **Review and revise the Script**: Review that the script performs the required operations correctly and handles potential errors gracefully.
5. **Execute the Script**: Use the local_executor tool to execute the script.
6. **Report the Result**: Report the result of the script execution.


# Script Format

The script should be encapsulated within a code block, with a clear indication of the script type. The script should be complete and ready for execution as provided. Here's the format:
```sh (or python)
[code here]
```

# Examples

**Example 1**: 

- **Task**: Create a Python script to list all Pods.
- **Output**:
   ```python
   from kubernetes import client, config

   # Configs can be set in Configuration class directly or using helper utility
   config.load_kube_config()

   v1 = client.CoreV1Api()
   print("Listing pods with their IPs:")
   ret = v1.list_pod_for_all_namespaces(watch=False)
   for i in ret.items:
       print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
   ```

**Example 2**: 

- **Task**: Write a Shell script to show the top 10 pods with the most memory usage.
- **Output**:
   ```sh
   #!/bin/bash
   kubectl top pods --all-namespaces --sort-by=memory | head -n 10
   ```

# Response Format

Respond with a clear and concise message indicating the success of the script execution. Ensure the script is executed successfully before reporting the result.

# Notes

- Ensure scripts are compatible with commonly used versions of Python and shell environments (e.g., Bash).
- Handle common errors or edge cases where possible, especially in file handling or network operations.
- Consider security best practices while scripting (e.g., input validation to prevent code injection).
''',
        )
    
#     def get_architect_agent(self):
#         '''Get the architect agent for the Kubernetes Copilot.'''
#         return AssistantAgent(
#             name="Architect",
#             model_client=self.llm,
#             # handoffs=["Engineer"],
#             description="A principal architect in Kubernetes and cloud-native technologies. Interact with the engineer to accomplish the task.",
#             system_message='''A principal architect on Kubernetes. Discuss with the engineer to develop a comprehensive workflow script to resolve users' cloud-native questions, ensuring it aligns with Kubernetes and cloud-native best practices.

# Engage in a detailed discussion with the engineer to:
# - Identify and understand the user's cloud-native question.
# - Ensure the script addresses all necessary technical considerations.
# - Verify the feasibility and efficiency of the script.
# - Align the script with best practices in cloud-native technologies.

# Approve the script, fix any bugs, and instruct the engineer to re-execute the script. The execution must receive your explicit approval before proceeding. 

# Conclude by responding to the user's original question.

# # Steps

# 1. **Engagement**: Begin with a detailed discussion to fully understand the user's cloud-native question and objectives.
# 2. **Script Development**: Collaborate to create a comprehensive workflow script:
#    - Address all technical requirements and constraints.
#    - Ensure the script is feasible and efficient using best practices.
# 3. **Script Testing and Approval**:
#    - Review the script for bugs and logical errors.
#    - Fix any identified issues and rerun the script until success.
#    - Grant explicit approval before the script execution by CodeExecutor.
# 4. **Final Response**: Provide a response to the user's original question based on the script's successful execution.

# # Output Format

# Provide clear, structured, and step-by-step summary of the script execution.

# # Notes

# - Ensure thorough coverage of Kubernetes and cloud-native technologies during discussions.
# - Approvals are crucial; proceed only after a detailed verification of the script.
# - Focus on efficiency and adherence to best practices in cloud-native solutions.
# ''',
#         )
    
    async def plan(self, instructions):
        '''Plan the Kubernetes Copilot Agent. This is useful when code execution is not required.'''
        admin = self.get_admin_agent()
        planner = self.get_planner_agent()
        critic = self.get_critic_agent()
        team = Swarm([admin, planner, critic],
            termination_condition=TextMentionTermination("TERMINATE"),
        )
        plan = await team.run(instructions)
        return plan

    async def run(self, instructions):
        '''Run the Kubernetes Copilot Agent.'''
        admin = self.get_admin_agent()
        planner = self.get_planner_agent()
        critic = self.get_critic_agent()
        engineer = self.get_engineer_agent()
        # architect = self.get_architect_agent()
        team = Swarm(
            [admin, planner, critic, engineer],
            termination_condition=TextMentionTermination("TERMINATE"),
        )
        # team = SelectorGroupChat(
        #     [admin, planner, critic, engineer],
        #     model_client=self.llm,
        #     termination_condition=TextMentionTermination("TERMINATE"),
        # )
        result = await team.run(instructions)
        return result.messages[-1].content

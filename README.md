# Autonomous Agent for Kubernetes

Autonomous Agent for Kubernetes powered by OpenAI.

Features:

- Autonomous Kubernetes cluster operations using LLM Agents powered by ChatGPT (GPT-3.5, GPT-4 and future versions).
- Diagnose and analyze the potential issues for Kubernetes workloads.
- Generate the Kubernetes manifests based on the provided prompt instructions.
- Utilize native kubectl and trivy commands for Kubernetes cluster access and security vulnerability scanning.

## Install

### Install locally

Install the kube-agent with the commands below. It is highly recommended to use [pipx](https://pipx.pypa.io/stable/) or [venv](https://docs.python.org/3/library/venv.html) to install the copilot to avoid conflicts with other Python packages.

```sh
# Option 1: use pipx to install the copilot
pipx install kube-agent

# Option 2: use venv to install the copilot
python3 -m venv agentenv
source agentenv/bin/activate
pip install kube-agent

# Option 3: Use pip to install the copilot (not recommended)
pip install kube-agent
```

**Setup:**

- Ensure [`kubectl`](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) is installed on the local machine and the kubeconfig file is configured for Kubernetes cluster access.
- Install [`trivy`](https://github.com/aquasecurity/trivy) to assess container image security issues (for the `audit` command).
- Set the OpenAI [API key](https://platform.openai.com/account/api-keys) as the `OPENAI_API_KEY` environment variable to enable ChatGPT functionality.
  - For [Azure OpenAI service](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/quickstart?tabs=command-line&pivots=rest-api#retrieve-key-and-endpoint), please set ` AZURE_OPENAI_API_KEY=<key>` and `AZURE_OPENAI_ENDPOINT=https://<replace-this>.openai.azure.com/`.


### Run in Kubernetes

```sh
kubectl run -it --rm copilot \
  --env="OPENAI_API_KEY=$OPENAI_API_KEY" \
  --restart=Never \
  --image=ghcr.io/feiskyer/kube-agent \
  -- execute --verbose 'What Pods are using max memory in the cluster'

kubectl run -it --rm copilot \
  --env="AZURE_OPENAI_API_KEY=$AZURE_OPENAI_API_KEY" \
  --env="AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT" \
  --restart=Never \
  --image=ghcr.io/feiskyer/kube-agent \
  -- execute --verbose 'What Pods are using max memory in the cluster'
```

Refer [kubernetes.md](kubernetes.md) for more detailed steps.

## How to use

Running directly in the terminal:

```sh
Usage: kube-agent [OPTIONS] COMMAND [ARGS]...

  Kubernetes Copilot powered by OpenAI

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  analyze   analyze issues for a given resource
  audit     audit security issues for a Pod
  diagnose  diagnose problems for a Pod
  execute   execute operations based on prompt instructions
  generate  generate Kubernetes manifests
```

### Audit Security Issues for Pod

`kube-copilot audit POD [NAMESPACE]` will audit security issues for a Pod:

```sh
Usage: kube-copilot audit [OPTIONS] POD [NAMESPACE]

  audit security issues for a Pod

Options:
  --verbose      Enable verbose information of copilot execution steps
  --model MODEL  OpenAI model to use for copilot execution, default is gpt-4
  --help         Show this message and exit.
```

### Diagnose Problems for Pod

`kube-copilot diagnose POD [NAMESPACE]` will diagnose problems for a Pod:

```sh
Usage: kube-copilot diagnose [OPTIONS] POD [NAMESPACE]

  diagnose problems for a Pod

Options:
  --verbose      Enable verbose information of copilot execution steps
  --model MODEL  OpenAI model to use for copilot execution, default is gpt-4
  --help         Show this message and exit.
```

### Analyze Potential Issues for k8s Object

`kube-copilot analyze RESOURCE NAME [NAMESPACE]` will analyze potential issues for the given resource object:

```sh
Usage: kube-copilot analyze [OPTIONS] RESOURCE NAME [NAMESPACE]

  analyze issues for a given resource

Options:
  --verbose     Enable verbose information of copilot execution steps
  --model TEXT  OpenAI model to use for copilot execution, default is gpt-4
  --help        Show this message and exit.
```

### Execute Operations Based on Prompt Instructions

`kube-copilot execute INSTRUCTIONS` will execute operations based on prompt instructions.
It could also be used to ask any questions.

```sh
Usage: kube-copilot execute [OPTIONS] INSTRUCTIONS

  execute operations based on prompt instructions

Options:
  --verbose      Enable verbose information of copilot execution steps
  --model MODEL  OpenAI model to use for copilot execution, default is gpt-4
  --help         Show this message and exit.
```

### Generate Kubernetes Manifests

Use the `kube-copilot generate` command to create Kubernetes manifests based on
the provided prompt instructions. After generating the manifests, you will be
prompted to confirm whether you want to apply them.

```sh
Usage: kube-copilot generate [OPTIONS] INSTRUCTIONS

  generate Kubernetes manifests

Options:
  --verbose     Enable verbose information of copilot execution steps
  --model TEXT  OpenAI model to use for copilot execution, default is gpt-4
  --help        Show this message and exit.
```

## Contribution

The project is opensource at github [feiskyer/kube-agent](https://github.com/feiskyer/kube-agent) with Apache License.

If you would like to contribute to the project, please follow these guidelines:

1. Fork the repository and clone it to your local machine.
2. Create a new branch for your changes.
3. Make your changes and commit them with a descriptive commit message.
4. Push your changes to your forked repository.
5. Open a pull request to the main repository.

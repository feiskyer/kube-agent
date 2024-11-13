#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import re
import traceback
import click

from kube_agent.agent import KubeCopilotAgent, AssistantAgent
from kube_agent.kubeconfig import setup_kubeconfig
from kube_agent.shell import CommandExecutor
from kube_agent.prompts import (
    get_prompt,
    get_diagnose_prompt,
    get_analyze_prompt,
    get_audit_prompt,
    get_generate_prompt
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")

cmd_options = [
    click.option("--verbose", default=True,
                 help="Enable verbose information of copilot execution steps"),
    click.option("--model", default="gpt-4o",
                 help="OpenAI model to use for copilot execution, default is gpt-4"),
]


def add_options(options):
    '''Add options to a command'''
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func
    return _add_options


@click.group()
@click.version_option()
def cli():
    '''Kubernetes Copilot powered by OpenAI'''


@cli.command(help="execute operations based on prompt instructions")
@click.pass_context
@click.argument('instructions', nargs=-1)
@add_options(cmd_options)
def execute(ctx, instructions, verbose, model):
    '''Execute operations based on prompt instructions'''
    if len(instructions) == 0:
        click.echo(ctx.get_help())
        ctx.exit()

    try:
        instructions = ' '.join(instructions)
        agent = KubeCopilotAgent(model, silent=not verbose)
        result = agent.run(get_prompt(instructions))
        print(result)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")


@cli.command(help="diagnose problems for a Pod")
@click.argument('pod')
@click.argument('namespace', default="default")
@add_options(cmd_options)
def diagnose(namespace, pod, verbose, model):
    '''Diagnose problems for a Pod'''
    try:
        agent = KubeCopilotAgent(model, silent=not verbose)
        result = agent.run(get_diagnose_prompt(namespace, pod))
        print(result)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")


@cli.command(help="audit security issues for a Pod")
@click.argument('pod')
@click.argument('namespace', default="default")
@add_options(cmd_options)
def audit(namespace, pod, verbose, model):
    '''Audit security issues for a Pod'''
    try:
        agent = KubeCopilotAgent(model, silent=not verbose)
        result = agent.run(get_audit_prompt(namespace, pod))
        print(result)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")


@cli.command(help="analyze issues for a given resource")
@click.argument('resource')
@click.argument('name')
@click.argument('namespace', default="default")
@add_options(cmd_options)
def analyze(resource, namespace, name, verbose, model):
    '''Analyze potential issues for a given resource'''
    try:
        agent = KubeCopilotAgent(model, silent=not verbose)
        result = agent.run(get_analyze_prompt(namespace, resource, name))
        print(result)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")


@cli.command(help="generate Kubernetes manifests")
@click.pass_context
@click.argument('instructions', nargs=-1)
@add_options(cmd_options)
def generate(ctx, instructions, verbose, model):
    '''Generate Kubernetes manifests'''
    if len(instructions) == 0:
        click.echo(ctx.get_help())
        ctx.exit()

    try:
        instructions = ' '.join(instructions)
        agent = AssistantAgent(model, silent=not verbose)
        result = agent.run(get_generate_prompt(instructions), instructions)
        print(result)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}")
        return

    # Apply the generated manifests in cluster
    if click.confirm('Do you approve to apply the generated manifests to cluster?'):
        yaml_blocks = re.findall(r'```yaml(.*?)```', result, re.DOTALL)
        manifests = '\n---\n'.join([b.strip() for b in yaml_blocks]) + '\n'
        print(CommandExecutor(command="kubectl", return_err_output=True).run(
            'kubectl apply -f -', input=bytes(manifests, 'utf-8')))


def main():
    '''Main function'''
    setup_kubeconfig()
    cli()


if __name__ == "__main__":
    main()

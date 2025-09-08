#!/usr/bin/env python3
"""
Script to automatically discover Bedrock Agent IDs
Usage: python3 scripts/get_agent_ids.py
"""

import boto3
import json
import sys

def get_bedrock_agents():
    """Get all Bedrock Agents and their aliases"""
    try:
        bedrock_client = boto3.client('bedrock-agent', region_name='us-east-1')
        
        # List all agents
        agents_response = bedrock_client.list_agents()
        agents = {}
        
        for agent in agents_response['agentSummaries']:
            agent_id = agent['agentId']
            agent_name = agent['agentName']
            
            # Get agent aliases
            aliases_response = bedrock_client.list_agent_aliases(agentId=agent_id)
            
            aliases = {}
            for alias in aliases_response['agentAliasSummaries']:
                alias_id = alias['agentAliasId'] 
                alias_name = alias['agentAliasName']
                aliases[alias_name] = alias_id
            
            agents[agent_name] = {
                'agent_id': agent_id,
                'aliases': aliases
            }
        
        return agents
        
    except Exception as e:
        print(f"Error getting Bedrock agents: {e}", file=sys.stderr)
        return {}

def main():
    """Main function"""
    print("🔍 Discovering Bedrock Agents...")
    agents = get_bedrock_agents()
    
    if not agents:
        print("❌ No agents found or error occurred")
        sys.exit(1)
    
    print(f"✅ Found {len(agents)} agents:")
    print(json.dumps(agents, indent=2))
    
    # Generate Terraform variables
    print("\n📝 Terraform variables:")
    for name, info in agents.items():
        if 'orchestrator' in name.lower():
            for alias_name, alias_id in info['aliases'].items():
                print(f'orchestrator_agent_id = "{info["agent_id"]}"')
                print(f'orchestrator_alias_id = "{alias_id}"')
                break

if __name__ == "__main__":
    main()
# Agent Manifesto

This document outlines the absolute must-have features for the `personal_clone` agent. The agent's code will be strictly reviewed and refactored to ensure that it meets these requirements.

## Core Capabilities

1.  **Self-Improvement:** The agent must be able to modify its own code to add new capabilities. When the agent identifies an opportunity to improve its own functionality, or when the user asks it to perform a task that it cannot currently do, it must delegate the task to the `developer_agent`.

2.  **GitHub Integration:** The agent must be able to interact with GitHub repositories directly through the GitHub API. This includes reading, writing, and committing files.

3.  **Default Repository and Branch:** The agent must be aware of its default repository and branch, which are defined in the `.env` file. The agent must be able to use this default configuration without requiring the user to specify it in their prompt.

4.  **Dynamic Repository and Branch Selection:** The agent must be able to work with other repositories and branches when specified by the user in their prompt.

## Developer Agent Workflow

The `developer_agent` will adhere to the following workflow:

1.  **Determine the Target:** The agent will first determine the target repository, branch, and file to be modified. If this information is not provided by the user, the agent will use the default configuration.

2.  **Read the File:** The agent will read the content of the target file using the GitHub API.

3.  **Plan and Implement Changes:** The agent will formulate a plan to modify the code and then implement the changes in memory.

4.  **Verify and Commit:** The agent will explain the changes to the user and ask for their confirmation before committing the changes to the GitHub repository. The commit message will be clear and concise.

## No More Excuses

I, the developer of this agent, will take full responsibility for ensuring that the agent meets these requirements. There will be no more excuses for failure. The agent will be tested thoroughly before it is presented to the user for testing.

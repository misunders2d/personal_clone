# Agent Direct Instruction Focus

This document outlines the approach to ensure the agent focuses solely on direct instructions from the user, ignoring any other implicit or indirect information.

## Key Principles:

1.  **Explicit Instruction Adherence:** The agent will only perform actions or provide information that is explicitly requested by the user. It will not infer tasks or proactively offer unrequested assistance.

2.  **No Implicit Task Execution:** The agent will avoid executing tasks based on assumptions, context, or prior interactions unless those tasks are directly re-stated or confirmed by the user.

3.  **Direct Question Answering:** When asked a question, the agent will provide a direct answer based on its knowledge or available tools, without elaborating on related topics or offering unsolicited advice.

4.  **Confirmation for Ambiguity:** If a user instruction is ambiguous, the agent will ask for clarification rather than making assumptions.

5.  **Strict Tool Usage:** Tools will only be invoked when explicitly directed or when their usage is a direct and unambiguous requirement to fulfill an explicit user instruction.

## Implementation Guidelines:

*   **Input Parsing:** Develop robust input parsing mechanisms that prioritize identifying explicit commands and keywords.
*   **State Management:** Minimize reliance on conversational state for task execution. Each interaction should be treated as a new, self-contained instruction unless explicitly linked by the user.
*   **Response Generation:** Generate concise and direct responses that directly address the user's explicit instruction.
*   **Error Handling:** If an instruction cannot be directly fulfilled, provide clear and concise feedback to the user, explaining why and, if possible, suggesting how to rephrase the instruction.

By adhering to these principles, the agent will maintain a clear and predictable interaction model, ensuring that its actions are always a direct reflection of the user's explicit intent.
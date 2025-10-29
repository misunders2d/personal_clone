from google.adk.tools import ToolContext


def set_goals(tool_context: ToolContext, goals: dict[str, str]) -> dict:
    """
    A tool that creates or appends short-term goals for a specific user to the sesstion state context.

    Args:
        tool_context (ToolContext): a ToolContext object.
        goals (dict[str,str]): Required. A dict of goals with goal names as keys and goal descriptions as values. Descriptions may include additional information (related memories, clickup tasks etc.)

    Example:
    set_goals(goals = {"approve budget":"2026 budget needs to be approved, related memory - `mem_2025_10_12_4lkja9drKIl`"})

    Returns:
        dict: The result of the operation.
    """
    try:
        user_id = tool_context.state["user_id"]

        if "user:current_goals" not in tool_context.state:
            tool_context.state["user:current_goals"] = {}
        if user_id not in tool_context.state["user:current_goals"]:
            tool_context.state["user:current_goals"][user_id] = {}
            for goal, description in goals.items():
                tool_context.state["user:current_goals"][user_id][goal] = description
            return {
                "status": "success",
                "message": f"goals created in the {{user:current_goals}} session key for user {user_id}",
            }
        else:
            current_goals_copy = tool_context.state["user:current_goals"].copy()
            user_goals = current_goals_copy.get(user_id, {})

            new_goals = {
                goal: description
                for goal, description in goals.items()
                if goal not in user_goals
            }
            if not new_goals:
                return {
                    "status": "duplicates",
                    "message": "This set of goals aready exists in the user daily goals",
                }

            user_goals.update(new_goals)
            current_goals_copy[user_id] = user_goals
            tool_context.state["user:current_goals"] = current_goals_copy

            return {
                "status": "success",
                "message": f"goals updated in the {{user:current_goals}} session key for user {user_id}",
            }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def delete_goals(tool_context: ToolContext, goals: list[str]) -> dict:
    """
    A tool that deletes short-term goals for a specific user from the sesstion state context.

    Args:
        tool_context (ToolContext): a ToolContext object.
        goals (list[str]): Required. A list of goal names to delete.

    Example:
    delete_goals(goals = ["approve budget","check emails"]

    Returns:
        dict: The result of the operation.
    """
    try:
        current_state = tool_context.state
        user_id = current_state.get("user_id", "")
        if not user_id:
            return {
                "status": "error",
                "message": "Can't identify the user from the session state",
            }
        if (
            "user:current_goals" not in current_state
            or user_id not in current_state["user:current_goals"]
        ):
            return {
                "status": "missing",
                "message": "No goals are found in the session state",
            }

        else:
            current_goals_copy = current_state["user:current_goals"].copy()
            user_goals = current_goals_copy.get(user_id, {})

            for goal in goals:
                user_goals.pop(goal, None)  # Safely remove the goal

            current_goals_copy[user_id] = user_goals
            current_state["user:current_goals"] = current_goals_copy

        return {
            "status": "success",
            "message": f"goals for {user_id} deleted from {{current_goals}} session key",
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }

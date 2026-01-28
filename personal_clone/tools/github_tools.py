# from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
# from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
# from mcp import StdioServerParameters
import github
from github import Github, Repository
from github.GithubException import GithubException
from google.adk.tools.tool_context import ToolContext

from .. import config

# def create_github_mcp_toolset():
#     try:
#         github_toolset = MCPToolset(
#             connection_params=StdioConnectionParams(
#                 server_params=StdioServerParameters(
#                     command="npx",
#                     args=[
#                         "-y",
#                         "@modelcontextprotocol/server-github",
#                     ],
#                     env={"GITHUB_PERSONAL_ACCESS_TOKEN": config.GITHUB_TOKEN},
#                 ),
#             ),
#         )
#         return github_toolset
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


# def create_adk_docs_mcp_toolset():
#     try:
#         adk_docs_mcp_toolset = MCPToolset(
#             connection_params=StdioConnectionParams(
#                 server_params=StdioServerParameters(
#                     command="uvx",
#                     args= [
#                         "--from",
#                         "mcpdoc",
#                         "mcpdoc",
#                         "--urls",
#                         "https://raw.githubusercontent.com/google/adk-docs/main/llms.txt",
#                         # "Local_ADK_Docs:/path/to/local/llms.txt"
#                         "--allowed-domains",
#                         "*",
#                         "--transport",
#                         "stdio"
#                     ]
#                 ),
#             ),
#         )
#         return adk_docs_mcp_toolset
#     except Exception as e:
#         return {"status": "error", "message": str(e)}


def create_github_toolset():

    try:
        g = (
            Github(auth=github.Auth.Token(config.GITHUB_TOKEN))
            if config.GITHUB_TOKEN
            else None
        )

        if not g:
            return {
                "status": "error",
                "error_message": "Github connection not initialized:",
            }

        def get_github_repo(
            tool_context: ToolContext, owner: str, repo_name: str
        ) -> dict:
            """
            Retrieves a GitHub repository object for further operations.
            Args:
                tool_context: ADK ToolContext for state/actions.
                owner: Repo owner (user/org name).
                repo_name: Repository name.
            Returns:
                dict: {'status': 'success'/'error', 'payload': repo_obj or None, 'error_message': str}.
            """
            try:
                repo: Repository.Repository = g.get_repo(f"{owner}/{repo_name}")
                tool_context.state["current_repo"] = repo
                return {
                    "status": "success",
                    "payload": {
                        "full_name": repo.full_name,
                        "default_branch": repo.default_branch,
                    },
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def list_repo_files(
            tool_context: ToolContext,
            repo_owner: str,
            repo_name: str,
            path: str,
            ref: str,
            recursive: bool,
        ) -> dict:
            """
            Lists files/directories in a repo path (recursive option via state flag).
            Args:
                tool_context: For caching repo and recursion flag.
                repo_owner: Repo owner.
                repo_name: Repo name.
                path: Directory path (e.g., 'src/').
                ref: Branch/commit/tag.
                recursive: `True` to list files in subdirectories, `False` otherwise
            Returns:
                dict: {'status': str, 'payload': list of {'name': str, 'path': str, 'type': 'file'/'dir', 'sha': str}}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                if recursive:
                    tree = repo.get_git_tree(ref, recursive=True)
                    files = [
                        {
                            "name": element.path.split("/")[-1],
                            "path": element.path,
                            "type": element.type,
                            "sha": element.sha,
                        }
                        for element in tree.tree
                        if path in element.path
                    ]
                else:
                    contents = repo.get_contents(path, ref=ref)
                    files = [
                        {
                            "name": c.name,
                            "path": c.path,
                            "type": "file" if c.type == "file" else "dir",
                            "sha": c.sha,
                        }
                        for c in contents  # type: ignore
                    ]
                return {"status": "success", "payload": files}
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def read_file_contents(
            repo_owner: str,
            repo_name: str,
            file_path: str,
            ref: str,
            tool_context: ToolContext,
        ) -> dict:
            """
            Reads the content of a specific file in the repo.
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                file_path: Full path to file (e.g., 'src/main.py').
                ref: Branch/commit/tag.
                tool_context: For caching.
            Returns:
                dict: {'status': str, 'payload': {'content': str (decoded), 'encoding': str}, 'error_message': str}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                file_content = repo.get_contents(file_path, ref=ref)
                content = file_content.decoded_content.decode("utf-8") if file_content.decoded_content else ""  # type: ignore
                return {"status": "success", "payload": {"content": content, "encoding": file_content.encoding, "sha": file_content.sha}}  # type: ignore
            except GithubException as e:
                return {
                    "status": "error",
                    "error_message": f"File not found or access denied: {e}",
                }

        def create_branch(
            repo_owner: str,
            repo_name: str,
            branch_name: str,
            from_branch: str,
            tool_context: ToolContext,
        ) -> dict:
            """
            Creates a new branch from an existing one.
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                branch_name: New branch name.
                from_branch: Source branch.
                tool_context: For logging actions.
            Returns:
                dict: {'status': str, 'payload': {'branch': branch_obj}, 'error_message': str}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                source_branch = repo.get_branch(from_branch)
                repo.create_git_ref(
                    f"refs/heads/{branch_name}", source_branch.commit.sha
                )
                new_branch = repo.get_branch(branch_name)
                return {
                    "status": "success",
                    "payload": {
                        "branch_name": new_branch.name,
                        "commit_sha": new_branch.commit.sha,
                    },
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def commit_to_branch(
            repo_owner: str,
            repo_name: str,
            branch_name: str,
            file_path: str,
            content: str,
            commit_message: str,
            tool_context: ToolContext,
        ) -> dict:
            """
            Commits a new/updated file to a branch (creates if missing).
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                branch_name: Target branch.
                file_path: File path (e.g., 'src/main.py').
                content: File content as string.
                commit_message: Commit message.
                tool_context: For state and actions.
            Returns:
                dict: {'status': str, 'payload': {'commit_sha': str}, 'error_message': str}.
            """
            if branch_name in ("master", "main"):
                return {
                    "status": "forbidden",
                    "message": "you must not commit to master/main branch",
                }
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                try:
                    existing_file = repo.get_contents(file_path, ref=branch_name)
                    result = repo.update_file(
                        file_path,
                        commit_message,
                        content,
                        existing_file.sha,  # type: ignore
                        branch=branch_name,
                    )
                except GithubException:  # File doesn't exist
                    result = repo.create_file(
                        file_path, commit_message, content, branch=branch_name
                    )
                commit = result["commit"]
                tool_context.state["last_commit_sha"] = commit.sha
                return {
                    "status": "success",
                    "payload": {
                        "commit_sha": commit.sha,
                        "commit_message": commit.commit.message,
                    },
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def create_pull_request(
            repo_owner: str,
            repo_name: str,
            title: str,
            body: str,
            head_branch: str,
            base_branch: str,
            tool_context: ToolContext,
        ) -> dict:
            """
            Creates a pull request from head to base branch.
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                title: PR title.
                body: PR description (optional).
                head_branch: Source branch (default: main).
                base_branch: Target branch (default: main).
                tool_context: For state.
            Returns:
                dict: {'status': str, 'payload': {'pr_url': str, 'pr_number': int}, 'error_message': str}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                pr = repo.create_pull(
                    title=title, body=body, head=head_branch, base=base_branch
                )
                tool_context.state["last_pr"] = {
                    "number": pr.number,
                    "url": pr.html_url,
                }
                return {
                    "status": "success",
                    "payload": {
                        "pr_number": pr.number,
                        "pr_url": pr.html_url,
                        "state": pr.state,
                    },
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def get_pr_details(
            repo_owner: str, repo_name: str, pr_number: int, tool_context: ToolContext
        ) -> dict:
            """
            Fetches details of a specific PR.
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                pr_number: PR number.
                tool_context: For caching.
            Returns:
                dict: {'status': str, 'payload': {'title': str, 'state': str, 'comments': int, 'commits': int}, 'error_message': str}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                pr = repo.get_pull(pr_number)
                return {
                    "status": "success",
                    "payload": {
                        "title": pr.title,
                        "body": pr.body,
                        "state": pr.state,
                        "comments": pr.comments,
                        "commits": len(list(pr.get_commits())),
                        "url": pr.html_url,
                    },
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def merge_pr(
            repo_owner: str,
            repo_name: str,
            pr_number: int,
            merge_method: str,
            commit_title: str,
            tool_context: ToolContext,
        ) -> dict:
            """
            Merges a PR (use cautiously; requires write perms).
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                pr_number: PR number.
                merge_method: 'merge', 'squash', or 'rebase'.
                commit_title: Custom merge commit title (optional).
            Returns:
                dict: {'status': str, 'payload': {'merged': bool, 'sha': str}, 'error_message': str}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                pr = repo.get_pull(pr_number)
                if commit_title:
                    pr.merge(merge_method=merge_method, commit_title=commit_title)
                else:
                    pr.merge(merge_method=merge_method)
                return {
                    "status": "success",
                    "payload": {"merged": True, "sha": pr.head.sha},
                }
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        def list_branches(
            repo_owner: str, repo_name: str, tool_context: ToolContext
        ) -> dict:
            """
            Lists all branches in the repo.
            Args:
                repo_owner: Repo owner.
                repo_name: Repo name.
                tool_context: For caching.
            Returns:
                dict: {'status': str, 'payload': list of {'name': str, 'commit_sha': str}}.
            """
            try:
                repo = tool_context.state.get("current_repo") or g.get_repo(
                    f"{repo_owner}/{repo_name}"
                )
                branches = [
                    {"name": b.name, "commit_sha": b.commit.sha}
                    for b in repo.get_branches()
                ]
                return {"status": "success", "payload": branches}
            except GithubException as e:
                return {"status": "error", "error_message": str(e)}

        return [
            get_github_repo,
            list_repo_files,
            read_file_contents,
            create_branch,
            commit_to_branch,
            create_pull_request,
            get_pr_details,
            list_branches,
        ]

    except Exception as e:
        return {"status": "error", "error_message": f"Github error: {e}"}


def return_github_toolset():
    # github_toolset = create_github_mcp_toolset()
    # if isinstance(github_toolset, dict) and github_toolset["status"] == "error":
    #     github_toolset = create_github_toolset()
    #     if isinstance(github_toolset, dict) and github_toolset["status"] == "error":
    #         return None
    github_toolset = create_github_toolset()
    return github_toolset

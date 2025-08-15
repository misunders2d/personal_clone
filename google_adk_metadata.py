import inspect
import json
import importlib
import pkgutil

ADK_MODULES = [
    "google.adk.agents",
    "google.adk.runners",
    "google.adk.tools",
    "google.adk.artifacts",
    "google.adk.sessions",
    "google.adk.tools.openapi_tool",
    "google.adk.errors",
]


def find_all_modules(base_packages):
    """
    Recursively finds all submodules for a given list of base packages.
    """
    all_modules = set(base_packages)
    for pkg_name in base_packages:
        try:
            pkg = importlib.import_module(pkg_name)
            # A package must have a __path__ attribute
            if hasattr(pkg, "__path__"):
                # Use walk_packages to find all submodules
                for _, module_name, _ in pkgutil.walk_packages(
                    pkg.__path__, prefix=pkg.__name__ + "."
                ):
                    all_modules.add(module_name)
        except ImportError:
            continue
    return sorted(list(all_modules))


def collect_adk_metadata():
    """
    Discovers all ADK modules and collects metadata in a hierarchical structure.
    """
    hierarchical_metadata = {}

    # The module list is already sorted, ensuring parent packages are processed before subpackages
    all_adk_modules_to_inspect = find_all_modules(ADK_MODULES)

    for module_name in all_adk_modules_to_inspect:
        try:
            module = importlib.import_module(module_name)

            # 1. First, collect all members defined in the current module
            module_members = {}
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj) or inspect.isfunction(obj)
                ) and obj.__module__ == module_name:
                    sig = None
                    try:
                        sig = str(inspect.signature(obj))
                    except (ValueError, TypeError):
                        pass

                    module_members[name] = {
                        "type": "class" if inspect.isclass(obj) else "function",
                        "signature": sig,
                        "doc": inspect.getdoc(obj) or "",
                    }

            # 2. If the module has members, place them in the hierarchy
            if not module_members:
                continue

            # 3. Navigate or create the nested structure based on the module name
            parts = module_name.split(".")
            current_level = hierarchical_metadata
            for part in parts:
                # setdefault gets the key if it exists, or creates it if it doesn't
                current_level = current_level.setdefault(part, {})

            # 4. Store the actual functions/classes under a special "__members__" key
            current_level["__members__"] = module_members

        except ImportError:
            continue

    return hierarchical_metadata


if __name__ == "__main__":
    meta = collect_adk_metadata()
    with open("adk_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

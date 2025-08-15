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
    "google.adk.errors"
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
            if hasattr(pkg, '__path__'):
                # Use walk_packages to find all submodules
                for _, module_name, _ in pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + '.'):
                    all_modules.add(module_name)
        except ImportError:
            continue
    return sorted(list(all_modules))

def collect_adk_metadata():
    """
    Discovers all ADK modules and collects metadata on their classes and functions.
    """
    metadata = {}
    
    # 1. First, discover all modules and submodules
    all_adk_modules_to_inspect = find_all_modules(ADK_MODULES)
    
    # 2. Then, iterate over the complete list to inspect them
    for module_name in all_adk_modules_to_inspect:
        try:
            module = importlib.import_module(module_name)
            metadata[module_name] = {}
            for name, obj in inspect.getmembers(module):
                # We only want classes or functions defined *in this specific module*
                if (inspect.isclass(obj) or inspect.isfunction(obj)) and obj.__module__ == module_name:
                    sig = None
                    try:
                        sig = str(inspect.signature(obj))
                    except (ValueError, TypeError):
                        pass  # Happens for some built-ins or C extensions
                    
                    metadata[module_name][name] = {
                        "type": "class" if inspect.isclass(obj) else "function",
                        "signature": sig,
                        "doc": inspect.getdoc(obj) or "",
                    }
        except ImportError:
            continue
            
    final_metadata = {k: v for k, v in metadata.items() if v}
    
    # Sort the final dictionary alphabetically by module name (the key)
    return dict(sorted(final_metadata.items())) # <-- MODIFIED LINE

if __name__ == "__main__":
    meta = collect_adk_metadata()
    with open("adk_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

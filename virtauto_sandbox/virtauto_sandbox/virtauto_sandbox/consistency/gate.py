
from typing import Tuple, List, Dict, Any

def preflight(task: Dict[str, Any]) -> Tuple[bool, List[str]]:
    return True, []

def postflight(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    return True, []

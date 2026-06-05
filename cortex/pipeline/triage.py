from dataclasses import dataclass, field
from typing import List, Any
from cortex.worker.issue_reader import IssueReader, IssueContext
from cortex.interfaces.memory_provider import MemoryProvider, MemoryResult

@dataclass
class TriageContext:
    issue: IssueContext
    related_memories: List[MemoryResult] = field(default_factory=list)
    architecture_context: List[Any] = field(default_factory=list)

class IssueTriagePipeline:
    """
    Sprint 2: Issue Reader -> CORTEX Search
    Pure pipeline coordinating the components without hard coupling.
    """
    def __init__(self, memory_provider: MemoryProvider):
        self.memory = memory_provider

    def process(self, issue_url: str) -> TriageContext:
        # Step 1: Deterministic Extraction
        issue = IssueReader.read(issue_url)
        
        # Step 2: Retrieve Relevant Context from Memory
        query = f"{issue.title}\n{issue.body}"
        
        # We query the interface, regardless of whether it's SQLite, Qdrant, or Mock
        related_memories = self.memory.search(query=query, limit=5)
        
        return TriageContext(
            issue=issue,
            related_memories=related_memories,
        )

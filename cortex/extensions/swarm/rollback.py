# [C5-REAL] Exergy-Maximized
"""
Safe Rollback Pattern for Cortex-Persist AST Mutations.
Implements Axiom AX-041: Tu repositorio de Git es tu base de datos inmutable. Rollback = git checkout.
Ensures thermodynamic equilibrium is restored if a JIT mutation fails structural validation.
"""

import subprocess
import logging
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

logger = logging.getLogger("cortex.extensions.swarm.rollback")

class MorphogeneticRollbackError(Exception):
    """Raised when an AST mutation is successfully rolled back after a failure."""
    pass

class DirtyWorkspaceError(Exception):
    """Raised when attempting to mutate a dirty workspace in strict mode."""
    pass

@contextmanager
def safe_ast_mutation_scope(repo_path: str | Path, strict_mode: bool = True) -> Generator[None, None, None]:
    """
    C5-REAL Safe Rollback Pattern for AST Mutations.
    
    Context manager that allows executing experimental AST mutations (JIT rewriting,
    genetic drift, Pliny-type fragmentations). If an exception is raised within the
    scope (e.g., TGI Cassandra validation fails), it immediately restores the working
    tree to its pristine state via Git, ensuring zero structural corruption.
    
    Args:
        repo_path: Absolute path to the Git repository.
        strict_mode: If True, refuses to run if the repository is already dirty before mutation.
    """
    repo_dir = str(repo_path)
    
    # 1. Evaluate baseline entropy (Git Status)
    status_cmd = subprocess.run(
        ["git", "status", "--porcelain"], 
        cwd=repo_dir, capture_output=True, text=True
    )
    if status_cmd.returncode != 0:
        raise MorphogeneticRollbackError("Target path is not a valid git repository or git error occurred.")
    
    is_dirty = len(status_cmd.stdout.strip()) > 0
    
    if strict_mode and is_dirty:
        raise DirtyWorkspaceError(
            "C5-REAL Violation: Cannot apply thermodynamic mutations to a dirty workspace. "
            "Commit or stash existing changes before triggering Sortu-APEX."
        )

    logger.info("⚡ [ROLLBACK-GUARD] Mutation scope opened. Workspace integrity verified.")

    try:
        # 2. Yield execution to the JIT mutator / Sortu-APEX
        yield
        
        # 3. If no exceptions, the mutation is thermodynamically stable
        logger.info("⚡ [ROLLBACK-GUARD] Mutation stabilized. Target morph achieved.")
        
    except Exception as e:
        # 4. Thermodynamic collapse or structural validation failure (e.g., TGI Block)
        logger.error(f"⚡ [ROLLBACK-GUARD] Structural failure detected: {str(e)}")
        logger.info("⚡ [ROLLBACK-GUARD] Initiating Git-level deterministic rollback...")
        
        try:
            # Revert all modified tracked files
            subprocess.run(["git", "restore", "."], cwd=repo_dir, check=True, capture_output=True)
            # Remove all untracked files introduced by the failed mutation
            subprocess.run(["git", "clean", "-fd"], cwd=repo_dir, check=True, capture_output=True)
            logger.info("⚡ [ROLLBACK-GUARD] Workspace restored to baseline zero-entropy state.")
        except subprocess.CalledProcessError as git_err:
            logger.critical(f"FATAL: Rollback mechanism failed. Workspace may be corrupted. {git_err.stderr}")
            raise MorphogeneticRollbackError("Catastrophic rollback failure") from git_err
            
        raise MorphogeneticRollbackError(f"AST mutation safely reverted due to underlying failure: {e}") from e

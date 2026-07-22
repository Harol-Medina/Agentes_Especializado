"""Abstract repository (git) access port."""

from abc import ABC, abstractmethod


class RepositoryPort(ABC):
    """Defines the contract for cloning and reading source repositories."""

    @abstractmethod
    async def clone(self, repo_url: str, dest_path: str) -> str:
        """
        Clone a remote repository to *dest_path*.

        Returns the local path of the cloned repository.

        Raises:
            RepositoryCloneError: If cloning fails for any reason.
            RepositoryTooLargeError: If the repository exceeds size/file limits.
        """
        ...

    @abstractmethod
    async def cleanup(self, repo_path: str) -> None:
        """Remove a previously cloned repository from local storage."""
        ...

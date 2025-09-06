"""
Presentation Factory - Dependency Injection Factory for MVC Components
Creates and configures MVC layer instances with proper dependency injection
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.compile_pptx import PresentationCompiler
from interfaces.presentation_controller_interface import (
    IPresentationCompiler,
    IPresentationControllerFactory,
    IPresentationOrchestrator,
    IQualityController,
)

# Import interfaces
from interfaces.presentation_model_interface import (
    IPresentationCache,
    IPresentationModel,
    IPresentationModelFactory,
    IPresentationValidator,
)
from interfaces.presentation_view_interface import (
    IPresentationTemplate,
)
from interfaces.presentation_view_interface import (
    IPresentationValidator as IViewValidator,
)
from interfaces.presentation_view_interface import (
    IPresentationView,
    IPresentationViewFactory,
)

# Import concrete implementations
from models.presentation_model import presentation_model

# Import utilities
from views.presentation_view import create_styled_presentation


class PresentationModelFactory(IPresentationModelFactory):
    """Factory for creating model layer instances"""

    def create_model(self, **config) -> IPresentationModel:
        """Create a presentation model instance"""
        # For now, use the singleton instance, but this can be extended
        # to support different model configurations
        return presentation_model

    def create_cache(self, **config) -> IPresentationCache:
        """Create a cache instance"""
        # This would be implemented when cache functionality is needed
        raise NotImplementedError("Cache implementation not yet available")

    def create_validator(self, **config) -> IPresentationValidator:
        """Create a validator instance"""
        # This would be implemented when validation functionality is needed
        raise NotImplementedError("Validator implementation not yet available")


class PresentationViewFactory(IPresentationViewFactory):
    """Factory for creating view layer instances"""

    def create_view(self, style: str, **config) -> IPresentationView:
        """Create a presentation view instance"""
        template_data = config.get("template_data")
        return create_styled_presentation(style, template_data)

    def create_template_manager(self, **config) -> IPresentationTemplate:
        """Create a template manager instance"""
        # This would be implemented when template manager is needed
        raise NotImplementedError("Template manager implementation not yet available")

    def create_validator(self, **config) -> IViewValidator:
        """Create a presentation validator instance"""
        # This would be implemented when validation functionality is needed
        raise NotImplementedError("View validator implementation not yet available")

    def get_supported_styles(self) -> List[str]:
        """Get list of supported presentation styles"""
        return ["professional", "creative", "minimalist", "technical"]


class PresentationControllerFactory(IPresentationControllerFactory):
    """Factory for creating controller layer instances"""

    def __init__(self):
        self.model_factory = PresentationModelFactory()
        self.view_factory = PresentationViewFactory()

    def create_compiler(
        self, model: IPresentationModel = None, view: IPresentationView = None, **config
    ) -> IPresentationCompiler:
        """Create a presentation compiler instance"""
        # Use provided instances or create new ones
        if model is None:
            model = self.model_factory.create_model(**config)

        # Note: view is typically created during compilation based on style
        return PresentationCompiler(model=model, view=view)

    def create_orchestrator(self, **config) -> IPresentationOrchestrator:
        """Create an orchestrator instance"""
        # This would be implemented when orchestrator functionality is needed
        raise NotImplementedError("Orchestrator implementation not yet available")

    def create_quality_controller(self, **config) -> IQualityController:
        """Create a quality controller instance"""
        # This would be implemented when quality control functionality is needed
        raise NotImplementedError("Quality controller implementation not yet available")

    def create_async_compiler(self, **config):
        """Create an async compiler instance"""
        raise NotImplementedError("Async compiler implementation not yet available")

    def create_batch_compiler(self, **config):
        """Create a batch compiler instance"""
        raise NotImplementedError("Batch compiler implementation not yet available")


class PresentationServiceProvider:
    """Main service provider for dependency injection"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_factory = PresentationModelFactory()
        self.view_factory = PresentationViewFactory()
        self.controller_factory = PresentationControllerFactory()

        # Cache instances to support singleton pattern where needed
        self._model_instance = None
        self._cached_views = {}

    def get_model(self) -> IPresentationModel:
        """Get model instance (singleton)"""
        if self._model_instance is None:
            self._model_instance = self.model_factory.create_model(**self.config)
        return self._model_instance

    def get_view(
        self, style: str, template_data: Optional[Dict[str, Any]] = None
    ) -> IPresentationView:
        """Get view instance (cached by style)"""
        cache_key = (
            f"{style}_{hash(str(template_data)) if template_data else 'default'}"
        )

        if cache_key not in self._cached_views:
            config = self.config.copy()
            if template_data:
                config["template_data"] = template_data
            self._cached_views[cache_key] = self.view_factory.create_view(
                style, **config
            )

        return self._cached_views[cache_key]

    def get_compiler(
        self,
        model: Optional[IPresentationModel] = None,
        view: Optional[IPresentationView] = None,
    ) -> IPresentationCompiler:
        """Get compiler instance"""
        if model is None:
            model = self.get_model()

        return self.controller_factory.create_compiler(
            model=model, view=view, **self.config
        )

    def create_configured_compiler(
        self,
        style: str = "professional",
        template_data: Optional[Dict[str, Any]] = None,
    ) -> IPresentationCompiler:
        """Create a fully configured compiler with all dependencies"""
        model = self.get_model()
        view = self.get_view(style, template_data)
        compiler = self.get_compiler(model=model)
        compiler.set_view(view)
        return compiler

    def cleanup(self):
        """Cleanup cached instances"""
        self._cached_views.clear()
        if self._model_instance and hasattr(self._model_instance, "cleanup"):
            self._model_instance.cleanup()


# Global service provider instance for backward compatibility
_service_provider = None


def get_service_provider(
    config: Optional[Dict[str, Any]] = None,
) -> PresentationServiceProvider:
    """Get global service provider instance"""
    global _service_provider
    if _service_provider is None or config is not None:
        _service_provider = PresentationServiceProvider(config)
    return _service_provider


def create_compiler_with_di(
    style: str = "professional",
    template_data: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> IPresentationCompiler:
    """Convenience function to create compiler with dependency injection"""
    provider = get_service_provider(config)
    return provider.create_configured_compiler(style, template_data)

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ModuleStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Version ES-module dependencies with their importer during collectstatic."""
    support_js_module_import_aggregation = True

"""
@module: app.services
@context: FastAPI backend — domain layer.
@role: Home for the project's domain/simulation logic (FE pre/post-processing,
       tooth-root stress evaluation, DIN 3990 / VDI 2736 calculations). Services
       read config via app.config, persist via app.storage / app.database, and
       cache disposable intermediates under Settings.cache_dir — never hardcode
       paths or open files directly (project_rules.md §16-17).
"""

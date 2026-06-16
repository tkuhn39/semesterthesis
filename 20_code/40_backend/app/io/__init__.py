"""
@module: app.io
@context: I/O layer.
@role: Typed parsers/writers (pydantic) for the gear toolchain's file formats —
       STplus `.ste`, REXS, STIRAK `.fsk`, Abaqus `.inp`/`.cof`, Z88. Each format
       gets its own module; services depend on these typed models, not on raw text.
"""

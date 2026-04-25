from setuptools import setup, Extension

setup(
    name='_native',
    ext_modules=[
        Extension(
            '_native',
            sources=['native_module.c'],
            extra_compile_args=['/O2', '/GL'],
            extra_link_args=['/LTCG'],
        )
    ],
)

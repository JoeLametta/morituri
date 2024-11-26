from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            name="accuraterip",
            libraries=['sndfile'],
            sources=["src/accuraterip-checksum.c"],
        ),
    ]
)

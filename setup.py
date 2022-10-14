import setuptools

setuptools.setup(
    name="toei_prober_system",
    version='0.1',
    description='Program for controlling TOEI magnetic prober system',
    author='Kotaro Taga',
    author_email='taga.kotaro.62d@st.kyoto-u.ac.jp',
    url='https://github.com/hoopdev/Toei_prober_system',
    license="MIT",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 1 - Planning"
    ],
    install_requires=[
        'numpy',
        'nidaqmx',
    ],
    python_requires='>=3.9',
)

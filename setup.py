"""
Setup configuration for Verdant-Minds (Unified Synthetic Mind)
A pioneering cognitive architecture with thermodynamic knowledge representation.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements from requirements.txt
def read_requirements(filename='requirements.txt'):
    """Read and parse requirements from requirements.txt file."""
    requirements = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments, empty lines, section headers, and -r references
            if line and not line.startswith('#') and not line.startswith('=') and not line.startswith('-r'):
                requirements.append(line)
    return requirements

# Core dependencies
install_requires = read_requirements('requirements.txt')

# Development dependencies (optional)
try:
    extras_require = {
        'dev': read_requirements('requirements-dev.txt')
    }
except FileNotFoundError:
    extras_require = {}

setup(
    # ========================================================================
    # Package Metadata
    # ========================================================================
    name='verdant-minds',
    version='0.2.0',
    author='captainkoopa420',
    author_email='adamswilliam905@gmail.com',
    description='A cognitive architecture for AI with quantum-inspired thermodynamic knowledge representation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/captainkoopa420/Verdant-Minds',
    project_urls={
        'Bug Tracker': 'https://github.com/captainkoopa420/Verdant-Minds/issues',
        'Documentation': 'https://github.com/captainkoopa420/Verdant-Minds#readme',
        'Source Code': 'https://github.com/captainkoopa420/Verdant-Minds',
    },

    # ========================================================================
    # License and Classification
    # ========================================================================
    license='MIT',
    classifiers=[
        # Development Status
        'Development Status :: 3 - Alpha',

        # Intended Audience
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',

        # Topic
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Python Modules',

        # License
        'License :: OSI Approved :: MIT License',

        # Python Versions
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',

        # Operating Systems
        'Operating System :: OS Independent',

        # Framework
        'Framework :: Robot Framework :: Library',
    ],
    keywords=[
        'artificial-intelligence',
        'cognitive-architecture',
        'quantum-computing',
        'ethical-ai',
        'knowledge-representation',
        'thermodynamics',
        'emergent-behavior',
        'consciousness',
        'machine-learning',
        'neural-networks',
    ],

    # ========================================================================
    # Package Discovery and Dependencies
    # ========================================================================
    packages=find_packages(
        include=['usm', 'usm.*'],
        exclude=['tests', 'tests.*', 'docs', 'docs.*']
    ),

    # Include the Verdant Source Codes directory as package data
    package_data={
        '': [
            'Verdant Source Codes/src/**/*.py',
            'Verdant Source Codes/src/**/__init__.py',
        ],
    },
    include_package_data=True,

    # Python version requirement
    python_requires='>=3.8',

    # Install dependencies
    install_requires=install_requires,

    # Optional dependencies
    extras_require=extras_require,

    # ========================================================================
    # Entry Points and Console Scripts
    # ========================================================================
    entry_points={
        'console_scripts': [
            # Main CLI entry point
            'verdant-minds=usm.__main__:main',
            'usm=usm.__main__:main',
        ],
    },

    # ========================================================================
    # Additional Configuration
    # ========================================================================
    zip_safe=False,  # Don't install as a zip file (better for debugging)

    # Test suite configuration
    test_suite='tests',

    # Additional metadata
    platforms=['any'],
)

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from datetime import datetime

# Add the project root directory to the path
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../lambdas'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'AI PPT Assistant'
copyright = f'{datetime.now().year}, AI PPT Assistant Team'
author = 'AI PPT Assistant Team'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
    'myst_parser',
    'sphinxcontrib.mermaid',
]

templates_path = ['_templates']
exclude_patterns = []

# Support for both .rst and .md files
source_suffix = ['.rst', '.md']

# MyST parser configuration
myst_enable_extensions = [
    "colon_fence",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "substitution",
    "tasklist",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# -- Extension configuration -------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Mock external dependencies for documentation generation
autodoc_mock_imports = ['boto3', 'botocore']

# Autodoc typehints settings
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'boto3': ('https://boto3.amazonaws.com/v1/documentation/api/latest/', None),
}

# Todo extension settings
todo_include_todos = True

# Copybutton settings
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# Mermaid settings
mermaid_version = "latest"
mermaid_init_js = "mermaid.initialize({startOnLoad:true});"

# Output file base name for HTML help builder.
htmlhelp_basename = 'AIPresentation'

# Custom CSS
html_css_files = [
    'custom.css',
]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_favicon = None

# Add custom logo
html_logo = None

# Show source link
html_show_sourcelink = True

# Show copyright
html_show_copyright = True

# Show sphinx
html_show_sphinx = True

# Language
language = 'zh_CN'

# Locale dirs
locale_dirs = ['locale/']
gettext_compact = False
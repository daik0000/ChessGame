import os
import sys
sys.path.insert(0, os.path.abspath('../../')) 

project = 'ChessGame'
copyright = '2025, Your Name'
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
]

intersphinx_mapping = {'python': ('https://docs.python.org/3', None),
                       'pygame': ('https://www.pygame.org/docs/', None)}

html_theme = 'sphinx_rtd_theme' 

autodoc_mock_imports = ['pygame'] 
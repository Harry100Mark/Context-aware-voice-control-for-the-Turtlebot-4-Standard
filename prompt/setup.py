from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'prompt'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Installiere JSON-Dateien und andere Ressourcen
        ('lib/python3.10/site-packages/' + package_name, ['prompt/roomlayout.json']),
        # Fewshots-Bilder und -Daten
        ('lib/python3.10/site-packages/' + package_name + '/fewshots', 
         glob('prompt/fewshots/*.png') + glob('prompt/fewshots/*.json')),
    ],
    install_requires=['setuptools', 'Pillow', 'google-generativeai'],
    zip_safe=True,
    maintainer='harryhundertmark',
    maintainer_email='harryhundertmark@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'prompt = prompt.prompt:main',
            'prompt_openai = prompt.prompt_openai:main',
            'prompt_google = prompt.prompt_google:main',
            'prompt_google2 = prompt.prompt_google2:main'
        ],
    },
)

from setuptools import find_packages, setup

package_name = 'audio_recorder'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(include=['audio_recorder', 'audio_recorder.*']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'numpy',
        'pyaudio',
        'webrtcvad',
    ],
    zip_safe=True,
    maintainer='harry',
    maintainer_email='harry@todo.todo',
    description='Audio recording with VAD for ReSpeaker 4 Mic Array',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'audio_recorder = audio_recorder.audio_recorder:main'
        ],
    },
)

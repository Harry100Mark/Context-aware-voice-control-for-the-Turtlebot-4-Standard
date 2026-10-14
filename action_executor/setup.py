from setuptools import find_packages, setup

package_name = 'action_executor'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'nav2_simple_commander',
    ],
    zip_safe=True,
    maintainer='harry',
    maintainer_email='harry@todo.todo',
    description='Executor for movement/navigate commands from prompt node',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'action_executor = action_executor.action_executor:main'
        ],
    },
)

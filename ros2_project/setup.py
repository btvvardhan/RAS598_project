import os
from glob import glob
from setuptools import setup

package_name = 'ros2_project'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/ament_index/resource_index/packages',
            ['resource/' + 'visualize.rviz']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*')),
        (os.path.join('share', package_name), glob('resource/*rviz'))
        # (os.path.join('share', package_name), ['scripts/TerminatorScript.sh'])
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Braden',
    maintainer_email='braden@arkelectron.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
                'offboard_control = ros2_project.offboard_control:main',
                'visualizer = ros2_project.visualizer:main',
                'velocity_control = ros2_project.velocity_control:main',
                'control = ros2_project.control:main',
                'image_saver = ros2_project.image_saver:main',
                'processes = ros2_project.processes:main',
                'coordinates = ros2_project.coordinates:main',
                'yolo = ros2_project.yolo:main',
                'camera_info_publisher = ros2_project.camera_info_publisher:main',
                'odometry_tf_broadcaster = ros2_project.odometry_tf_broadcaster:main'
                
        ],
    },
)

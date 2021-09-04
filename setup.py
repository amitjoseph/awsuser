from setuptools import setup, find_packages
  
with open('requirements.txt') as f:
    requirements = f.readlines()
  
long_description = ''
  
setup(
        name ='awsuser',
        version ='0.1.0',
        author ='Amit Joseph',
        author_email ='me@amitjoseph.com',
        url ='https://github.com/amitjoseph/awsuser',
        description ='Create and manage AWS users right from your terminal',
        long_description = long_description,
        long_description_content_type ="text/markdown",
        license ='GPL-3.0',
        packages = find_packages(),
        entry_points ={
            'console_scripts': [
                'awsuser = src.awsuser:main'
            ]
        },
        classifiers =[
            "Programming Language :: Python :: 3",
            "License :: GPL-3.0 License",
            "Operating System :: OS Independent",
        ],
        keywords ='awsuser aws iam cli amitjoseph',
        install_requires = requirements,
        zip_safe = False
)
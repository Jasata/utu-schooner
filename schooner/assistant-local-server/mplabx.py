#!/bin/env python3
#
#   Folder name
#   {assingment_id}-{uid}
import os
import shutil
from xml.etree import ElementTree as ET

MPLABXVERSION = "v5.45"
DEFAULT_ICON = "rO0ABXNyABVqYXZheC5zd2luZy5JbWFnZUljb27ypjVu3gwOMgMABUkABmhlaWdodEkABXdpZHRoTAARYWNjZXNzaWJsZUNvbnRleHR0ACtMamF2YXgvc3dpbmcvSW1hZ2VJY29uJEFjY2Vzc2libGVJbWFnZUljb247TAALZGVzY3JpcHRpb250ABJMamF2YS9sYW5nL1N0cmluZztMAA1pbWFnZU9ic2VydmVydAAeTGphdmEvYXd0L2ltYWdlL0ltYWdlT2JzZXJ2ZXI7eHAAAAAQAAAAEHBwcHcIAAAAEAAAABB1cgACW0lNumAmduqypQIAAHhwAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJZpaW7/ampv1Gpqb/9qam/Uampv/2pqb9Rqam//ampv1Gpqb/9qam/Uampv/2pqb5ZpaW4AAAAAAAAAAAAAAAD/ampv/87Ozv9qam//zs7O/2pqb//Ozs7/ampv/87Ozv9qam//zs7O/2pqb//Ozs7/ampvAAAAAAAAAADBam5y/2lrcP9qam//ampv/2pqb/9qam//ampv/2pqb/9qam//ampv/2pqb/9qam//ampv/2lrcMFqbnIAAAAA/2drcP/NztD/1dfY/9XX2P/V19j/1dfY/9XX2P/V19j/1dfY/9XX2P/V19j/1dfY/9XX2P/V19j/YGRpAAAAAP9mam//u72//7i6u/+4urv/uLq7/7i6u/+4urv/uLq7/7i6u/+4urv/uLq7/7i6u/+4urv/uLq7/2BkaQAAAAD/ZWlu/6uusP+rrrD/q66w/6uusP+rrrD/q66w/6uusP+rrrD/q66w/6uusP+rrrD/q66w/6uusP9gZGkAAAAA/2NnbP+ipaf/oqWn/6Klp//T1dX/09XV/9PV1f/T1dX/09XV/9PV1f/T1dX/oqWn/6Klp/9hY2T/YGRpAAAAAP9iZmv/m56h/5ueof+bnqH/tLe5/7S3uf+0t7n/tLe5/7S3uf+0t7n/m56h/5ueof+bnqH/XV9h/2BkaQAAAAD/YWVq/5eanf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf9gZGkAAAAA/2Bkaf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf+Xmp3/l5qd/5eanf+Xmp3/YGRpAAAAAP9WWl7/naCj/36Agv9+gIL/foCC/36Agv9+gIL/foCC/36Agv9+gIL/foCC/36Agv9+gIL/naCj/1ZaXgAAAADLNTk6/1ZXW/9qam//YmJn/2pqb/9iYmf/ampv/2JiZ/9qam//YmJn/2pqb/9iYmf/ampv/1ZXW8s1OToAAAAAJgAAAP9qam//7e3t/2pqb//t7e3/ampv/+3t7f9qam//7e3t/2pqb//t7e3/ampv/+3t7f9qam8mAAAAAAAAAAEAAACrXFxi/2pqb+NdXWL/ampv411dYv9qam/jXV1i/2pqb+NdXWL/ampv411dYv9qam+rXFxiAQAAAAAAAAAAAAAAHgAAADMAAAA4AAAAMwAAADgAAAAzAAAAOAAAADMAAAA4AAAAMwAAADgAAAAzAAAAHgAAAAAAAAB4"
PROJECT_XML  = os.path.join(
    os.path.expanduser("~"),
    f".mplab_ide/dev/{MPLABXVERSION}/config/Preferences/org/netbeans/modules",
    "projectui.properties"
)

class MPLABXProject:
    """MPLAB X Project class for Schooner assistant local service needs."""
    # Naming:
    # .path = /dir0/dir1/dir2/
    # .folder = dir2

    # Hardcoded, because XML sucks to high-heavens...
    xpath = "{http://www.netbeans.org/ns/project/1}configuration/{http://www.netbeans.org/ns/make-project/1}data/{http://www.netbeans.org/ns/make-project/1}name"

    def __init__(self, src: str, uid: str, aid: str):
        """Argument is a MPLAB X project directory ("project_name.X" or similar). 'uid' is the user ID of the student and 'aid' is the assignment ID."""
        self.folder = os.path.basename(os.path.normpath(src))
        self.path   = src
        self.uid    = uid
        self.aid    = aid
        self.deployfolder = f"{aid}-{uid}.X"
        self.deploypath   = os.path.join(
            os.path.expanduser("~"),
            "MPLABXProjects",
            self.deployfolder
        )
        # Few basic checks
        if (
            not os.path.isdir(self.path) or
            not os.path.isfile(os.path.join(self.path, "Makefile")) or
            not os.path.isfile(os.path.join(self.path, "nbproject/project.xml")) or
            not os.path.isfile(os.path.join(self.path, "nbproject/configurations.xml"))
        ):
            raise Exception(
                f"Directory '{self.path}' does not appear to be a valid MPLAB X project directory!"
            )
        #self.name = self.__project_name()



    @property
    def name(self) -> str:
        """Reads {dir}/nbproject/project.xml and returns the project name"""
        # Reading from SOURCE
        self.xmlfile = os.path.join(self.path, "nbproject/project.xml")
        if not os.path.isfile(self.xmlfile):
            raise Exception(f"File '{self.xmlfile}' does not exist!")
        tree = ET.parse(self.xmlfile)
        node = tree.find(MPLABXProject.xpath)
        if node is None:
            raise Exception(
                f"Project name was not found in the nbproject/project.xml file!"
            )
        return node.text

    @name.setter
    def name(self, value:str) -> None:
        """Call AFTER .deploy() because this will modify the target XML."""
        self.xmlfile = os.path.join(self.path, "nbproject/project.xml")
        if not os.path.isfile(self.xmlfile):
            raise Exception(f"File '{self.xmlfile}' does not exist!")
        tree = ET.parse(self.xmlfile)
        node = tree.find(MPLABXProject.xpath)
        if node is None:
            raise Exception(
                f"Project name was not found in the nbproject/project.xml file!"
            )
        node.text = value
        tree.write(self.xmlfile)


    def deploy(self):
        """Copies the project directory to target folder."""
        print(self.path, "=>", self.deploypath)
        if os.path.exists(self.deploypath):
            try:
                shutil.rmtree(self.deploypath)
            except:
                raise
        shutil.copytree(self.path, self.deploypath)
        # TODO: move is more appropriate for this use case.
        #shutil.move(
        #    self.path,
        #    os.path.join(self.projectroot)
        #)




class MPLABXProjectUIProperties(dict):

    def __init__(self, filename: str):
        self.filename = filename


    def __enter__(self):
        with open(self.filename) as file:
            for line in file:
                key, val = line.split("=", 1)
                self[key] = val.strip()
        self.__coalesce()
        return self


    def __exit__(self, type, value, traceback):
        with open(self.filename, "w") as file:
            for k, v in self.items():
                if k == 'openProjects':
                    index = 0
                    for item in v:
                        for k, v in item.items():
                            file.write(f"openProjects{k}.{index}={v}\r\n")
                        index += 1
                else:
                    file.write(f"{k}={v}\r\n")
        return True



    def __coalesce(self):
        """converts 'openProjects*' into a list of dictionaries."""
        self['openProjects'] = []
        try:
            for i in range(0, 10000):
                self['openProjects'].append(
                    {
                        'DisplayNames' : self.pop(f"openProjectsDisplayNames.{i}"),
                        'Icons' : self.pop(f"openProjectsIcons.{i}"),
                        'URLs' : self.pop(f"openProjectsURLs.{i}")
                    }
                )
        except KeyError as e:
            # Expected and normal "exit"
            pass


    def indexof(self, projectdir: str) -> int:
        import re
        # Last directory in a path, optionally ending with "/"
        pattern = re.compile(f".*\/{re.escape(projectdir)}[\/]?$")
        return next(
            (
                i for i, item, in enumerate(self['openProjects'])
                if pattern.match(item['URLs'])
            ),
            None
        )


    def remove(self, folder:str):
        print(f"Looking for '{folder}'")
        index = self.indexof(folder)
        if index:
            print(f"'{folder}' found at index {index}")
            del self['openProjects'][index]


    def add(self, project, set_as_main: bool = True) -> None:
        """Takes project object as an argument."""
        self['openProjects'].append(
            {
                'DisplayNames' : project.name,
                'Icons' : DEFAULT_ICON,
                'URLs' : "file:" + (
                    project.deploypath
                    if project.deploypath.endswith('/')
                    else project.deploypath + '/'
                )
            }
        )
        if set_as_main:
            self['mainProjectURL'] = "file:" + project.deploypath
            # If it doesn't end with '/', the main project is not set
            if not self['mainProjectURL'].endswith('/'):
                self['mainProjectURL'] += '/'



if __name__ == '__main__':

    with MPLABXProjectUIProperties(PROJECT_XML) as projectxml:
        projectxml.remove('serial_echo_3.X')

        project = MPLABXProject("/home/dte20074/Clock.X", "jasata", "E01")
        print(project.name, "Will be deployed as", project.deployfolder)
        project.deploy()
        # Set project name to match {aid}-{uid}
        project.name = project.deployfolder[:-2]
        projectxml.add(project)

# EOF

# Max-Planck-Institution for Radioastronmy (MPIfR),
# Bonn, Auf dem Huegel 69
#
# Beam weight calculation tool.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import paramiko
import base64
import sys
import os
from os import path
import re


"""
 Description:
 ------------
    Simple SSH client based on paramiko

Institution: Max-Planck Institution for Radioastronomy (MPIfR-Bonn)
    Auf dem Huegel 69, Bonn, Germany

Author: Niclas Eesser <nesser@mpifr-bonn.mpg.de>

Changelog :
    - Ver 1.0000   : Initial version (2020 08 28)
"""


def resolve_directory(dir):
    """
    Description:
    ------------
       Parses a string that contains a directory, username and host address
    Parameters:
    -----------
        :param dir: Directory to parse (dtype str)
    """
    list = re.split('@|:', dir)
    if len(list) == 3:
        username = list[0]
        host = list[1]
        folder = list[2]
    elif len(list) == 1:
        username = None
        host = None
        folder = list[0]
    else:
        print("Error: Could not resolve directory")
        sys.exit(1)
    return username, host, folder


class SSHConnector():
    """
    Description:
    ------------
        A class that allows to connect via SSH.

    Attributes
    ----------
        host : str
            A string that represents the remote host address
        username : str
            Name of user
        password : str
            Passowrd of user
        port : int
            Port to connect to remote host
        gss_auth: bool
            Kerberos authentication based on gssapi. If desired set to True
        client: SSHClient
            Instance of paramiko's SSHClient class. Provides the connection to a remote server.
        ftp_client: SFTPClient
            Instance of paramiko's SFTPClient class. Allows to down- and upload files.

    Methods
    -------
        connect()
            Connects to a server by given attributes that are passed to constructor
        download(src_file, dst_file)
            Uses the SFTP client to download one file
        upload(src_file, dst_file)
            Uses the SFTP client to upload one file
        download_files(src_dir, dst_dir, fnames)
            Uses SFTPClient to download several files
        upload_files(src_dir, dst_dir, fnames)
            Uses SFTPClient to upload several files
        close()
            Closes the connection of SFTPClient and SSHClient
    """
    def __init__(self, host=None, username=None, password=None, port=22, gss_auth=True, gss_kex=True):
        """
        Description:
        ------------
            Constructor of class SSHConnector

        Parameters:
        -----------
            All parameters passed to constructor already described in class description
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.gss_auth = gss_auth
        self.gss_kex = gss_kex
        paramiko.util.log_to_file("log/ssh.log")

    def connect(self):
        """
        Description:
        ------------
            Connects to a server by given attributes that are passed to constructor

        Parameters:
        -----------
            None
        """
        print("Trying to connect: " + str(self.username) + "@"+ str(self.host) + ":" + str(self.port))
        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Try usual SSH connection
            try:
                self.client.connect(hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password)
            except Exception as e:
                print("*** Could not connect via SSH: " + str(e.__class__) + ": " + str(e))
                print("Therefore trying to authenticate with Kerberos ticket...")
                # If exception occurs; try to connect with Kerberos ticket authentication
                try:
                    self.client.connect(hostname=self.host,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        gss_auth=self.gss_auth,
                        gss_kex=self.gss_kex)
                except Exception as e:
                    print("*** Could not connect via Kerberos; Error: " + str(e.__class__) + ": " + str(e))
                    sys.exit(1)
        except Exception as e:
            print("*** Caught exception: %s: %s" % (e.__class__, e))
            traceback.print_exc()
            try:
                self.client.close()
            except:
                pass
            sys.exit(1)
        self.ftp_client = self.client.open_sftp()

    def download(self, src_file, dst_file):
        """
        Description:
        ------------
            Uses the SFTP client to download one file.

        Parameters:
        -----------
            :param src_file: String that contains directory + filename of one file on remote system,
                which should be downloaded.
            :param dst_file: String that contains directory + filename of one file on local system.
                If the directory does not exist, it will be created.

        """
        try:
            os.mkdir(dst_dir)
        except:
            pass
        self.ftp_client.get(src_file, dst_file)

    def upload(self, src_file, dst_file):
        """
        Description:
        ------------
            Uses the SFTP client to upload one file

        Parameters:
        -----------
            :param src_file: String containing directory + filename of one file on local system,
                which should be uploaded.
            :param dst_file: String containing directory + filename of one file on remote system.
                If the directory does not exists the upload will fail.

        """
        self.ftp_client.put(src_file, dst_file)

    def download_files(self, src_dir, dst_dir, fnames):
        """
        Description:
        ------------
            Downloads a set of files passed as a list.

        Parameters:
        -----------
            :param src_dir: String containing the directory where the files to be downloaded are located (remote).
            :param dst_dir: String containing the directory where the files should be stored (local).
            :param fnames: List of files
        Returns:
        --------
            A list of all downloaded files
        """
        if src_dir[-1] != "/":
            src_dir += "/"
        stdin, stdout, stderr = self.client.exec_command("cd " + src_dir + " && ls " + fnames)
        file_list = [f.replace('\n', '') for f in stdout.readlines()]
        if not len(file_list):
            print("Error: No file found in source directory " + src_dir + " that matches: " + fnames +" ...")
            sys.exit(1)

        print("Found " + str(len(file_list)) + " files in directory " + src_dir)
        for f_idx, f_name in enumerate(file_list):
            print("Downloading file " + str(f_idx) + ": " + f_name + "...")
            self.download(src_dir + f_name, dst_dir + f_name)
        return file_list

    def upload_files(self, src_dir, dst_dir, fnames):
        """
        Description:
        ------------
            Uploads a one or serveral files that is passed as a list.

        Parameters:
        -----------
            :param src_dir: String containing the directory where the files to be downloaded are located (remote).
            :param dst_dir: String containing the directory where the files should be stored (local).
            :param fnames: List or string containing files
        """
        if src_dir[-1] != "/":
            src_dir += "/"
        if type(fnames) is not list:
            file_list = [fnames]
        else:
            file_list = fnames
        for f_idx, f_name in enumerate(file_list):
            if path.exists(src_dir + f_name):
                print("Uploading file " + str(f_idx) + ": " + dst_dir + f_name + " ...")
                self.upload(src_dir + f_name, dst_dir + f_name)
            else:
                print("File " + src_dir + f_name + " does not exist!")


    def close(self):
        """
        Description:
        ------------
            Closes the connection of opened clients.

        Parameters:
        -----------
            None
        """
        print("Closing connection")
        try:
            self.ftp_client.close()
        except:
            pass

        try:
            self.client.close()
        except:
            pass

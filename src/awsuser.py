#!/bin/python3

import boto3, botocore
from src import utils
import argparse
from tabulate import tabulate
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow

class AccessKeyExists(Exception):
    pass

class MFAExists(Exception):
    pass

class user:
    def __init__(self,username):
        self.username = username
        self.password = ""
        self.account_alias = utils.get_account_alias()
        self.console_url = f"https://{self.account_alias}.signin.aws.amazon.com/console"
        self.iam = boto3.resource('iam')
        self.client = boto3.client('iam')

        self.user = self.iam.User(username)
        self.login_profile = self.user.LoginProfile()
        self.access_keys = self._get_accesskey_list()
        self.mfa_devices = self._get_mfa_devices()
        self.groups = self.get_groups()

        self.mfa_secret_key = ""
        self.access_key_pair  = ""

    def _get_accesskey_list(self):
        try:
            ak = self.client.list_access_keys(UserName=self.username)
            return ak['AccessKeyMetadata']
        except self.client.exceptions.NoSuchEntityException:
            return []

    def _get_mfa_devices(self):
        try:
            md = self.client.list_mfa_devices(UserName=self.username)
            return md['MFADevices']
        except self.client.exceptions.NoSuchEntityException:
            return []

    def _user_exist(self):
        try:
            self.user.load()
            return True
        except self.client.exceptions.NoSuchEntityException as err:
            return False
    
    def _login_exist(self):
        try:
            self.login_profile.load()
            return True
        except self.client.exceptions.NoSuchEntityException as err:
            return False

    def _accesskeys_exist(self):
        try:
            self.access_keys = self._get_accesskey_list()
            if len(self.access_keys) > 0:
                print(self.access_keys)
                return True
            else:
                False
        except boto3.exceptions.ResourceLoadException as err:
            return False

    def _mfa_exists(self):
        self._get_mfa_devices()
        if len(self.mfa_devices) > 0:
            return True
        else:
            return False

    def create_user(self):
        if not self._user_exist():
            self.user.create()
        else:
            print(f"User {self.username} already Exists")


    def delete_user(self):
        if self._user_exist():
            self.delete_mfa()
            self.delete_all_accesskeys()
            self.delete_login()
            self.remove_from_all_groups()
            self.user.delete()

    
    def create_login(self,custom_password=""):
        try:
            if self._login_exist():
                print(f"Login Profile already exists for {self.username}")
            else:
                self.password = custom_password if custom_password else utils.get_random_password()
                self.login_profile.create(
                    Password=self.password,
                    PasswordResetRequired=True
                    )
        except Exception as e:
            print(f"Could not create login Profile for {self.username}")
            raise(e)

    def reset_login(self,custom_password=""):
        try:
            if self._login_exist():
                    print(f"Reseting Login Profile for {self.username}")
                    self.password = custom_password if custom_password else utils.get_random_password()
                    self.login_profile.update(
                        Password=self.password,
                        PasswordResetRequired=True
                    )
            else:
                print(f"Login Profile does not exists for {self.username}")

        except Exception as e:
            print(f"Could not reset login Profile for {self.username}")
            raise(e)

    def create_accesskeys(self,reset=False,create_if_not_exist=True):
        try:
            if len(self.access_keys) == 2:
                print(f"Two Access Key Pairs already exists for {self.username}")
                raise AccessKeyExists   
            if len(self.access_keys) > 0 and create_if_not_exist:
                print(f"Access Key Pair already exists for {self.username}")
                raise AccessKeyExists  
            self.access_key_pair = self.user.create_access_key_pair()
            self.access_keys = self._get_accesskey_list()
            # print(self.access_key_pair)
        except AccessKeyExists:
            pass
        except Exception as e:
            print(f"Could not create Access Keys for {self.username}")
            raise(e)

    def _remove_unassigned_mfa(self):
        response = self.client.list_virtual_mfa_devices(
                    AssignmentStatus='Unassigned')
        for mfa in response['VirtualMFADevices']:
            if self.username in mfa['SerialNumber'].split('/'):
                print("Deleting the Unassigned Virtual MFA Device:",mfa)
                self.client.delete_virtual_mfa_device(SerialNumber=mfa['SerialNumber'])
                break


    def enable_mfa(self):
        try:
            if len(self.mfa_devices) > 0:
                raise MFAExists
            retry_count=2
            while True:
                retry_count-=1
                if retry_count < 0:
                    break
                try:
                    response = self.client.create_virtual_mfa_device(
                        VirtualMFADeviceName=self.username)
                    break
                except self.client.exceptions.EntityAlreadyExistsException:
                    self._remove_unassigned_mfa()
                except Exception as e:
                    print("Something went wrong generating MFA")
                    raise(e)

            # print(response)

            mfa_serial_key = response['VirtualMFADevice']['SerialNumber']
            self.mfa_secret_key = response['VirtualMFADevice']['Base32StringSeed']

            # print(self.mfa_secret_key)
            tokens = utils.get_mfa_tokens(self.mfa_secret_key)

            mfa_device = self.user.MfaDevice(mfa_serial_key)
            mfa_device.associate(
                AuthenticationCode1=tokens[0],
                AuthenticationCode2=tokens[1]
            )
            self.mfa_devices = self._get_mfa_devices()

        except MFAExists:
            print(f"MFA already exists for {self.username}")
        except Exception as e:
            print(f"Could not create MFA for {self.username}")  
            raise(e)  
    

    def delete_login(self):
        try:
            if self._login_exist():
                self.login_profile.delete()
        except Exception as e:
            print(f"Could not delete login for {self.username}")  
            raise(e)


    def delete_accesskey(self,access_key_id):
        try:
            access_key = self.user.AccessKey([access_key_id])
            access_key.delete()
        except Exception as e:
            print(f"Could not delete access key pair ({access_key_id}) for {self.username}")  
            raise(e)

    def delete_all_accesskeys(self):
        for pair in self.access_keys:
            self.delete_accesskey(pair['AccessKeyId'])
            # access_key = self.user.AccessKey(pair['AccessKeyId'])
            # access_key.delete()

    def delete_mfa(self):
        if len(self.mfa_devices) > 0:
            mfa_serial_number = self.mfa_devices[0]['SerialNumber']
            mfa_device = self.user.MfaDevice(mfa_serial_number)
            mfa_device.disassociate()
            self.client.delete_virtual_mfa_device(SerialNumber=mfa_serial_number)
        else:
            print("No MFA exist!")

    def get_user_status(self):
        table_data=[]
        table_data.append((bold(yellow("Username")),bold(self.username)))
        table_data.append((green("--------"),""))
        table_data.append((bold("Groups"), ", ".join(self.get_groups()) ))
        table_data.append((green("--------"),""))
        table_data.append((bold("Last Login"),self.user.password_last_used if self._login_exist() else "Disabled",utils.check_recent_use(self.user.password_last_used)))
        table_data.append((green("--------"),""))
        table_data.append((bold("MFA"),"Enabled" if self._mfa_exists() else "None"))
        table_data.append((green("--------"),""))
        for key in self.access_keys:
            ## Last used 
            response = self.client.get_access_key_last_used(AccessKeyId=key['AccessKeyId'])
            last_used = response['AccessKeyLastUsed']
            table_data.append((bold("AccessKey"),key['AccessKeyId']))
            table_data.append((bold("ServiceName"),last_used.get('ServiceName')))
            table_data.append((bold("Region"),last_used.get('Region')))
            table_data.append((bold("LastUsedDate"),last_used.get('LastUsedDate'), utils.check_recent_use(last_used.get('LastUsedDate'))))
            table_data.append((green("--------"),""))
        print(tabulate(table_data,tablefmt='plain'))

    
    def get_login_details(self):
        # return self.username,self.password,self.console_url

        table_data=[]
        if self.password:
            table_data.append(("Console Url",self.console_url))
            table_data.append(("Username",self.username))
            table_data.append(("Password",self.password))

        if self.access_key_pair:
            table_data.append(("AccessKeyId",self.access_key_pair.id))
            table_data.append(("AccessKeySecret",self.access_key_pair.secret))

        if self.mfa_secret_key:
            table_data.append(("MFA Secret",self.mfa_secret_key))

        print(tabulate(table_data,tablefmt='plain'))


    
    def check_sub_resources(self):
        pass

    def get_groups(self):
        try:
            groups = self.user.groups.all()
            return [g.group_name for g in groups]
        except self.client.exceptions.NoSuchEntityException:
            return []

    def add_to_groups(self,group_names):
        for group in group_names:
            try:
                response = self.user.add_group(
                        GroupName=group
                    )
                print(f"Added user {self.username} to group {group}")
            except self.client.exceptions.NoSuchEntityException:
                print(f"Could not find group : {group}")
            except:
                print(f"Could not add to group {group} for {self.username}")
    
    def remove_from_groups(self,group_names):
        for group in group_names:
            try:
                response = self.user.remove_group(
                        GroupName=group
                    )
                print(f"Removed user {self.username} from group {group}")
            except:
                print(f"Could not remove from group {group} for {self.username}")

    def remove_from_all_groups(self):
        group_names = self.get_groups()
        self.remove_from_groups(group_names)


         

def main():
    parser = argparse.ArgumentParser(description='aws user managemant tool')
    parser.add_argument('command',action='store',choices=["create","reset-console-login","delete","search","describe"])
    parser.add_argument('username',action='store')
    parser.add_argument('--login',action='store_true')
    parser.add_argument('--access-keys',action='store_true')
    parser.add_argument('--mfa',action='store_true')
    parser.add_argument('--force','-f',action='store_true')
    parser.add_argument('--groups',type=str)
    parser.add_argument('--verbose','-v',action='store_true')
    # parser.add_argument('--profile',action='store') ##WIP 

    args = parser.parse_args()

    if args.command == "create":
        u = user(args.username)
        u.create_user()
        if args.login:
            u.create_login()
        if args.access_keys:
            u.create_accesskeys()
        if args.mfa:
            u.enable_mfa()
        if args.groups:
            group_list = [x.strip() for x in args.groups.split(',')]
            u.add_to_groups(group_list)

        u.get_login_details()

    elif args.command == "delete":
        u = user(args.username)
        u.get_user_status()
        if not args.force:
            x = input(f"Do you want to delete the user {u.username} ? (y/n) :")
            if x != 'y':
                exit(0)
        u.delete_user()

    elif args.command == "reset-console-login":
        u = user(args.username)
        if u._user_exist():
            u.get_user_status()
        u.create_login(reset=True)
        print(u.get_login_details())

    elif args.command == "search":
        print(utils.filter_username(args.username))

    elif args.command == "describe":
        u = user(args.username)
        if u._user_exist():
            u.get_user_status()
        else:
            print(f"{args.username} does not exists!")

    else:
        pass
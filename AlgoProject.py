import pdb
import os
import datetime
import getpass
import pickle
import argparse
from typing import Any, Dict

from prettytable import PrettyTable

############### Global Resources ###############


card_rate = {
    'amex': 0.8,
    'visa': 1.0,
    'discover': 0.5
}

convenience_fee_rate = 0.2


############### Classes ###############


class Purchase:
    ''' Class to model purchases '''

    def __init__(self, date: datetime.date, card: str, amount: float,
                 status: bool = False):
        ''' Initializer '''
        # Purchase date
        self.date = date
        # Card type
        assert card in card_rate, 'Unsupported card type: {}. The only \
            supported types are: {}.'.format(card, list(card_rate.keys()))
        self.card = card
        # Status
        self.status = status  # False indicates 'due' and True indicates 'paid'
        # Amounts and fees
        self.amount = amount
        if not self.status:
            self._transaction_fee = self.amount * card_rate[self.card] / 100
            self._convenience_fee = self.amount * convenience_fee_rate / 100
        else:
            self._transaction_fee = 0
            self._convenience_fee = 0
        self.final_amount = self.amount + \
                            self._transaction_fee + \
                            self._convenience_fee
        # Billing cycle
        start_date = self.date.replace(day=1)
        if self.date.month == 12:
            end_date = self.date.replace(year=self.date.year + 1, month=1, day=1) - datetime.timedelta(days=1)
        else:
            end_date = self.date.replace(month=self.date.month + 1, day=1) - datetime.timedelta(days=1)
        self.billing_cycle = '{}, {}'.format(start_date, end_date)

    def __repr__(self):
        return '{}: Amount {} on {} for card {} [Cycle: {}]'.format('Purchase' if not self.status else 'Payment',
                                                                    self.final_amount, self.date, self.card,
                                                                    self.billing_cycle)


class PurchaseLog:
    ''' Data structure to store log of purchases for a user '''

    def __init__(self):
        ''' Initializer '''
        self.log = []
        self.min_purchase = None
        self.max_purchase = None
        self.total_due = 0
        self.total_paid = 0

    def add_purchase(self, purchase):
        ''' Implements binary search to insert a new purchase based on its
            date.
        '''
        # Insert purchase in log
        if len(self.log) == 0:
            self.log.insert(0, purchase)
            if not purchase.status:
                self.min_purchase = purchase
                self.max_purchase = purchase
        else:
            ## Binary search for insertion
            _start = 0
            _end = len(self.log) - 1
            while _end - _start > 1:
                _mid = (_start + _end) // 2
                if self.log[_mid].date > purchase.date:
                    _end = _mid - 1
                else:
                    _start = _mid + 1
            if purchase.date < self.log[_start].date:
                self.log.insert(_start, purchase)
            elif purchase.date >= self.log[_end].date:
                self.log.insert(_end + 1, purchase)
            else:
                self.log.insert(_end, purchase)
            ## Update min and max purchase
            if not purchase.status:
                if self.min_purchase is None:
                    self.min_purchase = purchase
                elif self.min_purchase.final_amount > purchase.final_amount:
                    self.min_purchase = purchase
                if self.max_purchase is None:
                    self.max_purchase = purchase
                elif self.max_purchase.final_amount < purchase.final_amount:
                    self.max_purchase = purchase
        # Update totals
        if not purchase.status:
            self.total_due += purchase.final_amount
        else:
            self.total_paid += purchase.final_amount

    def query_totals(self):
        return self.total_due, self.total_paid

    def query_purchases(self, status=False):
        return [p for p in self.log if p.status == status]


class UserAccount:
    ''' Class for a user account '''

    def __init__(self, name: str, fullname: str, phone_num: str, \
                 password: str, country: str, address: str):
        ''' Initializer '''
        self.name = name
        self.fullname = fullname
        self.phone_num = phone_num
        self.password = password
        self.country = country
        self.address = address
        self.purchase_log = PurchaseLog()


class Platform:
    ''' Class for the payment platform '''

    def __init__(self, userdatafile='users.pkl'):
        ''' Initializer '''
        self.current_user = None
        self.userdatafile = userdatafile
        # Load or create user accounts database
        if os.path.exists(userdatafile) and os.path.isfile(userdatafile):
            with open(userdatafile, 'rb') as f:
                userdata = pickle.load(f)
        else:
            with open(userdatafile, 'wb') as f:
                userdata = {}
                pickle.dump(userdata, f)
        self.userdata = userdata

    def create_account(self):
        ''' Create new user account '''
        # Username
        while True:
            uname = input('Please enter your desired username: ')
            if uname in self.userdata:
                print('Username: {} already exists. Please use a different \
                    name.'.format(uname))
            else:
                print('Username: {} accepted.'.format(uname))
                break
        # Password
        while True:
            passwd = input('Please enter your password: ')
            passwd2 = input('Please confirm your password: ')
            if passwd == passwd2:
                print('Passwords match. Your new password has been accepted.')
                break
            else:
                print('Passwords do not match. Please try again.')
        # More info
        fullname = input('Please enter your full name: ')
        phone_num = input('Please enter your phone number: ')
        country = input('Please enter your country of residence: ')
        address = input('Please provide your full address: ')
        # Create user account
        uaccount = UserAccount(name=uname, fullname=fullname, \
                               phone_num=phone_num, password=passwd, country=country, \
                               address=address)
        # Add to database
        self.userdata[uname] = uaccount
        with open(self.userdatafile, 'wb') as f:
            pickle.dump(self.userdata, f)
        print('New user account successfully created')

    def login(self):
        ''' Function to log a user in '''
        # Username
        uname = input('Please enter your username: ')
        if uname not in self.userdata:
            print('Unknown username: {}'.format(uname))
            return
        # Password
        passwd = input('Please enter your password: ')
        if passwd == self.userdata[uname].password:
            self.current_user = uname
            print('Login Successful.')
        else:
            print('Incorrect password.')

    def logout(self):
        ''' Function to log a user out '''
        # Dump the current logs back to file
        with open(self.userdatafile, 'wb') as f:
            pickle.dump(self.userdata, f)
        # Log user out
        self.current_user = None
        print('Successfully logged out.')

    def display_info(self):
        ''' Function to query your information '''
        if self.current_user is not None:
            print('Username: {}'.format(self.userdata[self.current_user].name))
            print('Password: {}'.format(self.userdata[self.current_user].password))
            print('Full name: {}'.format(self.userdata[self.current_user].fullname))
            print('Phone number: {}'.format(self.userdata[self.current_user].phone_num))
            print('Country: {}'.format(self.userdata[self.current_user].country))
            print('Address: {}'.format(self.userdata[self.current_user].address))

    def upload_purchase(self):
        ''' Upload a purchase '''
        if self.current_user is not None:
            # Get transaction info
            datestring = input('Enter date in format YYYY-MM-DD: ')
            date = datetime.date.fromisoformat(datestring)
            card = input('Enter card type: ').lower()
            assert card in card_rate, 'Acceptable card types are: {}'.format(list(card_rate.keys()))
            amount = float(input('Enter amount: '))
            statusstr = input('Enter 1 for payment or defaults to purchase: ')
            status = True if int(statusstr) == 1 else False
            # Generate transaction
            p = Purchase(date, card, amount, status)
            self.userdata[self.current_user].purchase_log.add_purchase(p)

            # Dump the current logs back to file
            with open(self.userdatafile, 'wb') as f:
                pickle.dump(self.userdata, f)
            print('Transaction logged: {}'.format(p))

    def query_minmax(self):
        ''' Returns the minimum and maximum transactions '''
        if self.current_user is not None:
            print('Minimum purchase:')
            print(self.userdata[self.current_user].purchase_log.min_purchase)
            print('Maximum purchase:')
            print(self.userdata[self.current_user].purchase_log.max_purchase)

    def print_totals(self):
        ''' Print total paid, total due and remaining amount due '''
        if self.current_user is not None:
            total_due, total_paid = self.userdata[self.current_user].purchase_log.query_totals()
            print('Total due till date: {}'.format(total_due))
            print('Total paid till date: {}'.format(total_paid))
            print('Remaining amount due: {}'.format(total_due - total_paid))

    def print_payment_history(self):
        ''' Print tabular history of all payments '''
        if self.current_user is not None:
            # Generate table
            table = PrettyTable(['Date (YYYY-MM-DD)', 'Card', 'Amount paid', 'Billing Cycle'])
            payments = self.userdata[self.current_user].purchase_log.query_purchases(True)
            for p in payments:
                table.add_row([p.date, p.card, p.final_amount, p.billing_cycle])
            print(table)

    def print_purchase_history(self):
        ''' Print tabular history of all purchases '''
        if self.current_user is not None:
            # Obtain date range
            d1 = input('Enter start date in format YYYY-MM-DD: ')
            d1 = datetime.date.fromisoformat(d1)
            d2 = input('Enter end date in format YYYY-MM-DD: ')
            d2 = datetime.date.fromisoformat(d2)
            # Generate table
            table = PrettyTable(['Date (YYYY-MM-DD)', 'Card', 'Amount paid', 'Billing Cycle'])
            purchases = self.userdata[self.current_user].purchase_log.query_purchases(False)
            for p in purchases:
                if d1 <= p.date <= d2:
                    table.add_row([p.date, p.card, p.final_amount, p.billing_cycle])
            print(table)

    def launch(self):
        ''' Launches the UI loop for platform '''
        # Login screen
        while self.current_user is None:
            print('\n***Welcome to the Titan Payment Platform***')
            print('1. Create a new account')
            print('2. Login to an existing account')
            print('3. Exit')
            O1 = input('Please select an option to proceed: ')
            try:
                O1 = int(O1)
            except Exception:
                print('Incorrect option. Please enter 1, 2 or 3 to proceed.')
            if O1 == 1:
                # Create new account
                self.create_account()
            elif O1 == 2:
                # Log in
                self.login()
                # Logged in screen
                while self.current_user is not None:
                    print('\nWelcome back, {}!'.format( \
                        self.userdata[self.current_user].fullname))
                    print('1. Display user info')
                    print('2. Upload a purchase')
                    print('3. Show minimum and maximum transaction')
                    print('4. Show amount due and total paid')
                    print('5. Retrieve payment history')
                    print('6. Display purchase history')
                    print('7. Log out')
                    O2 = input('Please select an option to proceed: ')
                    try:
                        O2 = int(O2)
                    except Exception:
                        print('Incorrect option. Please enter a number in 1-7 to proceed.')
                    if O2 == 1:
                        # Display user info
                        self.display_info()
                    elif O2 == 2:
                        # Upload a purchase
                        self.upload_purchase()
                    elif O2 == 3:
                        # Show minimum and maximum transaction
                        self.query_minmax()
                    elif O2 == 4:
                        # Show amount due and total paid
                        self.print_totals()
                    elif O2 == 5:
                        # Retrieve payment history
                        self.print_payment_history()
                    elif O2 == 6:
                        # Display purchase history
                        self.print_purchase_history()
                    elif O2 == 7:
                        # Log out
                        self.logout()
                    else:
                        print('Incorrect option. Please enter a number in 1-7 to proceed.')
            elif O1 == 3:
                break
            else:
                print('Incorrect option. Please enter 1, 2 or 3 to proceed.')


############### Main ###############


if __name__ == '__main__':
    # Parse arguments
    parser = argparse.ArgumentParser(description='Payment System Launcher.')
    parser.add_argument('-udf', '--userdatafile',
                        type=str, default='users.pkl',
                        help='User data file.')
    args = parser.parse_args()

    # Launch platform
    Platform(args.userdatafile).launch()
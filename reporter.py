#!/usr/bin/python
# -*- coding: utf-8 -*-

# Reporting tool for querying Sales- and Financial Reports from iTunes Connect
#
# This script mimics the official iTunes Connect Reporter by Apple which is used
# to automatically retrieve Sales- and Financial Reports for your App Store sales.
# It is written in pure Python and doesn’t need a Java runtime installation.
# Opposed to Apple’s tool, it can fetch iTunes Connect login credentials from the
# macOS Keychain in order to tighten security a bit. Also, it goes the extra mile
# and unzips the downloaded reports if possible.
#
# Copyright (c) 2016 fedoco <fedoco@users.noreply.github.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse, urllib, urllib2, json, zlib, datetime
import sys
if sys.platform == 'darwin':
    import keychain

VERSION = '2.1'
ENDPOINT_SALES = 'https://reportingitc-reporter.apple.com/reportservice/sales/v1'
ENDPOINT_FINANCE = 'https://reportingitc-reporter.apple.com/reportservice/finance/v1'

# queries

def get_vendors(credentials):
    command = 'Sales.getVendors'
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_status(credentials, service):
    command = service + '.getStatus'
    endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, credentials, command))

def get_accounts(credentials, service):
    command = service + '.getAccounts'
    endpoint = ENDPOINT_SALES if service == 'Sales' else ENDPOINT_FINANCE
    output_result(post_request(endpoint, credentials, command))

def get_vendor_and_regions(credentials):
    command = 'Finance.getVendorsAndRegions'
    output_result(post_request(ENDPOINT_FINANCE, credentials, command))

def get_specific_sales_report(credentials, vendor, reporttype, datetype, date, version):
    command = 'Sales.getReport, {0},{1},Detailed,{2},{3},{4}'.format(reporttype, vendor, datetype, date, version)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_specific_demographics_report(credentials, vendor, reporttype, datetype, date, version):
    command = 'Sales.getReport, {0},{1},Summary,{2},{3},{4}'.format(reporttype, vendor, datetype, date, version)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_financial_report(credentials, vendor, regioncode, fiscalyear, fiscalperiod):
    command = 'Finance.getReport, {0},{1},Financial,{2},{3}'.format(vendor, regioncode, fiscalyear, fiscalperiod)
    output_result(post_request(ENDPOINT_FINANCE, credentials, command))

def get_sales_report(credentials, vendor, datetype, date):
    command = 'Sales.getReport, {0},Sales,Summary,{1},{2}'.format(vendor, datetype, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_subscription_report(credentials, vendor, date):
    command = 'Sales.getReport, {0},Subscription,Summary,Daily,{1}'.format(vendor, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_subscription_event_report(credentials, vendor, date):
    command = 'Sales.getReport, {0},SubscriptionEvent,Summary,Daily,{1}'.format(vendor, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_subscriber_report(credentials, vendor, date):
    command = 'Sales.getReport, {0},Subscriber,Detailed,Daily,{1}'.format(vendor, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_newsstand_report(credentials, vendor, datetype, date):
    command = 'Sales.getReport, {0},Newsstand,Detailed,{1},{2}'.format(vendor, datetype, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command))

def get_opt_in_report(credentials, vendor, date):
    command = 'Sales.getReport, {0},Sales,Opt-In,Weekly,{1}'.format(vendor, date)
    output_result(post_request(ENDPOINT_SALES, credentials, command), False) # do not attempt to unzip because it's password protected

# HTTP request

def build_json_request_string(credentials, query):
    """Build a JSON string from the urlquoted credentials and the actual query input"""

    userid, password, accessToken, account, mode = credentials
    request_data = dict(version=VERSION, mode=mode, queryInput=query)

    if userid: request_data.update(userid=userid)
    if account: request_data.update(account=str(account)) # empty account info would result in error 404 
    if password: request_data.update(password=password)
    if accessToken: request_data.update(accesstoken=accessToken)

    request = {k: urllib.quote_plus(v) for k, v in request_data.items()}
    request = json.dumps(request)

    return 'jsonRequest=' + request

def post_request(endpoint, credentials, command):
    """Execute the HTTP POST request"""

    command = "[p=Reporter.properties, %s]" % command
    request_data = build_json_request_string(credentials, command)
    request = urllib2.Request(endpoint, request_data)
    request.add_header('Accept', 'text/html,image/gif,image/jpeg; q=.2, */*; q=.2')

    try:
        response = urllib2.urlopen(request)
        content = response.read()
        header = response.info()

        return (content, header)
    except urllib2.HTTPError, e:
        if e.code == 400 or e.code == 401 or e.code == 403 or e.code == 404:
            # for these error codes, the body always contains an error message
            raise ValueError(e.read())
        else:
            raise ValueError("HTTP Error %s. Did you choose reasonable query arguments?" % str(e.code))

def output_result(result, unzip = True):
    """Output (and when necessary unzip) the result of the request to the screen or into a report file"""

    content, header = result

    # unpack content into the final report file if it is gzip compressed.
    if header.gettype() == 'application/a-gzip':
        msg = header.dict['downloadmsg']
        filename = header.dict['filename'] or 'report.txt.gz'
        if unzip:
            msg = msg.replace('.txt.gz', '.txt')
            filename = filename[:-3]
            content = zlib.decompress(content, 15 + 32)
        file = open(filename, 'w')
        file.write(content)
        file.close()
        print msg
    else:
        print content

# command line arguments

def parse_arguments():
    """Build and parse the command line arguments"""

    parser = argparse.ArgumentParser(description="Reporting tool for querying Sales- and Financial Reports from iTunes Connect", epilog="For a detailed description of report types, see http://help.apple.com/itc/appssalesandtrends/#/itc37a18bcbf")

    # (most of the time) optional arguments
    parser.add_argument('-a', '--account', type=int, help="account number (needed if your Apple ID has access to multiple accounts; for a list of your account numbers, use the 'getAccounts' command)")
    parser.add_argument('-m', '--mode', choices=['Normal', 'Robot.XML'], default='Normal', help="output format: plain text or XML (defaults to '%(default)s')")
    parser.add_argument('-u', '--userid', help="Apple ID for use with iTunes Connect")
    
    # always required arguments
    required_args = parser.add_argument_group("required arguments")
    mutex_group = required_args.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument('-t','--access-token-keychain-item', help='name of the macOS Keychain item that holds the access token')
    mutex_group.add_argument('-T','--access-token', help='Access token (can be generated in iTunes Connect - Sales & Trends - Reports - About Reports)')
    mutex_group.add_argument('-p', '--password-keychain-item', help="DEPRECATED: name of the macOS Keychain item that holds the Apple ID password (cannot be used together with -P)")
    mutex_group.add_argument('-P', '--password', help="DEPRECATED: Apple ID password (cannot be used together with -p)")
    
    # commands
    subparsers = parser.add_subparsers(dest='command', title='commands', description="Specify the task you want to be carried out (use -h after a command's name to get additional help for that command)")
    parser_01 = subparsers.add_parser('getStatus', help="check if iTunes Connect is available for queries")
    parser_01.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")

    parser_02 = subparsers.add_parser('getAccounts', help="fetch a list of accounts accessible to the Apple ID given in -u")
    parser_02.add_argument('service', choices=['Sales', 'Finance'], help="service endpoint to query")

    parser_03 = subparsers.add_parser('getVendors', help="fetch a list of vendors accessible to the Apple ID given in -u")

    parser_04 = subparsers.add_parser('getVendorsAndRegions', help="fetch a list of financial reports you can download by vendor number and region")

    parser_05 = subparsers.add_parser('getFinancialReport', help="download a financial report file for a specific region and fiscal period")
    parser_05.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_05.add_argument('regioncode', help="two-character code of country of the report to download (for a list of country codes by vendor number, use the 'getVendorsAndRegions' command)")
    parser_05.add_argument('fiscalyear', help="four-digit year of the report to download (year is specific to Apple’s fiscal calendar)")
    parser_05.add_argument('fiscalperiod', help="period in fiscal year for the report to download (1-12; period is specific to Apple’s fiscal calendar)")

    parser_06 = subparsers.add_parser('getSalesReport', help="download a summary sales report file for a specific date range")
    parser_06.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_06.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_06.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")

    parser_07 = subparsers.add_parser('getSubscriptionReport', help="download a subscription report file for a specific day")
    parser_07.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_07.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")

    parser_08 = subparsers.add_parser('getSubscriptionEventReport', help="download an aggregated subscriber activity report file for a specific day")
    parser_08.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_08.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")

    parser_09 = subparsers.add_parser('getSubscriberReport', help="download a transaction-level subscriber activity report file for a specific day")
    parser_09.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_09.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")

    parser_10 = subparsers.add_parser('getNewsstandReport', help="download a magazines & newspapers report file for a specific date range")
    parser_10.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_10.add_argument('datetype', choices=['Daily', 'Weekly'], help="length of time covered by the report")
    parser_10.add_argument('date', help="specific time covered by the report (weekly reports, like daily reports, use YYYYMMDD, where the day used is the Sunday that week ends")

    parser_11 = subparsers.add_parser('getOptInReport', help="download contact information for customers who opt in to share their contact information with you")
    parser_11.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_11.add_argument('date', help="specific day covered by the report (use YYYYMMDD format)")

    parser_12 = subparsers.add_parser('getSpecificSalesReport', help="download a sales report file for a specific report type and date or calendar unit")
    parser_12.add_argument('reporttype', choices=['Sales', 'PreOrder', 'Cloud', 'Event', 'Customer', 'Content', 'Station', 'Control', 'amEvent', 'amContent', 'amControl', 'amStreams'], help="report type according to documentation from Apple")
    parser_12.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_12.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_12.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
    parser_12.add_argument('version', nargs="?", help="Report version formatted like '1_0' or '1_1'", default="1_0")

    parser_13 = subparsers.add_parser('getSpecificDemographicsReport', help="download a demographics report file for a specific report type and date or calendar unit")
    parser_13.add_argument('reporttype', choices=['amContentDemographics', 'amArtistDemographics', 'ContentDemographics', 'ArtistDemographics'], help="report type according to documentation from Apple")
    parser_13.add_argument('vendor', type=int, help="vendor number of the report to download (for a list of your vendor numbers, use the 'getVendors' command)")
    parser_13.add_argument('datetype', choices=['Daily', 'Weekly', 'Monthly', 'Yearly'], help="length of time covered by the report")
    parser_13.add_argument('date', help="specific time covered by the report (weekly reports use YYYYMMDD, where the day used is the Sunday that week ends; monthly reports use YYYYMM; yearly reports use YYYY)")
    parser_13.add_argument('version', nargs="?", help="Report version formatted like '1_0' or '1_1'", default="1_0")
	
    return parser.parse_args()

def validate_arguments(args):
    """Do some additional checks on the passed arguments which argparse couldn't handle directly"""

    if args.password_keychain_item:
       try:
           keychain.find_generic_password(None, args.password_keychain_item, '')
       except:
           raise ValueError("Error: Could not find an item named '{0}' in the default Keychain".format(args.password_keychain_item))

    if args.access_token_keychain_item:
       try:
           keychain.find_generic_password(None, args.access_token_keychain_item, '')
       except:
           raise ValueError("Error: Could not find an item named '{0}' in the default Keychain".format(args.access_token_keychain_item))

    if not args.account and (args.command == 'getVendorsAndRegions' or args.command == 'getVendors' or args.command == 'getFinancialReport'):
        raise ValueError("Error: Argument -a/--account is needed for command '%s'" % args.command)

    if hasattr(args, 'fiscalyear'):
        try:
            datetime.datetime.strptime(args.fiscalyear, "%Y")
        except:
            raise ValueError("Error: Fiscal year must be specified as YYYY")

    if hasattr(args, 'fiscalperiod'):
       try:
           if int(args.fiscalperiod) < 1 or int(args.fiscalperiod) > 12:
               raise Exception
       except:
           raise ValueError("Error: Fiscal period must be a value between 1 and 12")

    if hasattr(args, 'datetype'):
        format = '%Y%m%d'
        error = "Date must be specified as YYYYMMDD for daily reports"
        if args.datetype == 'Weekly':
            error = "Date must be specified as YYYYMMDD for weekly reports, where the day used is the Sunday that week ends"
        if args.datetype == 'Monthly':
            error = "Date must be specified as YYYYMM for monthly reports"
            format = '%Y%m'
        if args.datetype == 'Yearly':
            error = "Date must be specified as YYYY for yearly reports"
            format = '%Y'
        try:
            datetime.datetime.strptime(args.date, format)
        except:
            raise ValueError("Error: " + error)

# main

if __name__ == '__main__':
    args = parse_arguments()

    try:
      validate_arguments(args)
    except ValueError, e:
      print e
      exit(-1)

    password = keychain.find_generic_password(None, args.password_keychain_item, '') if args.password_keychain_item else args.password
    access_token = keychain.find_generic_password(None, args.access_token_keychain_item, '') if args.access_token_keychain_item else args.access_token

    credentials = (args.userid, password, access_token, args.account, args.mode)

    try:
      if args.command == 'getStatus':
          get_status(credentials, args.service)
      elif args.command == 'getAccounts':
          get_accounts(credentials, args.service)
      elif args.command == 'getVendors':
          get_vendors(credentials)
      elif args.command == 'getVendorsAndRegions':
          get_vendor_and_regions(credentials)
      elif args.command == 'getSalesReport':
          get_sales_report(credentials, args.vendor, args.datetype, args.date)
      elif args.command == 'getSpecificSalesReport':
          get_specific_sales_report(credentials, args.reporttype, args.vendor, args.datetype, args.date, args.version)
      elif args.command == 'getSpecificDemographicsReport':
          get_specific_demographics_report(credentials, args.reporttype, args.vendor, args.datetype, args.date, args.version)
      elif args.command == 'getFinancialReport':
          get_financial_report(credentials, args.vendor, args.regioncode, args.fiscalyear, args.fiscalperiod)
      elif args.command == 'getSubscriptionReport':
          get_subscription_report(credentials, args.vendor, args.date)
      elif args.command == 'getSubscriptionEventReport':
          get_subscription_event_report(credentials, args.vendor, args.date)
      elif args.command == 'getSubscriberReport':
          get_subscriber_report(credentials, args.vendor, args.date)
      elif args.command == 'getNewsstandReport':
          get_newsstand_report(credentials, args.vendor, args.datetype, args.date)
      elif args.command == 'getOptInReport':
          get_opt_in_report(credentials, args.vendor, args.date)
    except ValueError, e:
       print e
       exit(-1)

    exit(0)

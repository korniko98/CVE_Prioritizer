#!/usr/bin/env python3
# This file contains the functions that create the reports

import os
import requests

from dotenv import load_dotenv
from termcolor import colored

from scripts.constants import EPSS_URL
from scripts.constants import NIST_BASE_URL

__author__ = "Mario Rojas"
__license__ = "BSD 3-clause"
__version__ = "1.3.0"
__maintainer__ = "Mario Rojas"
__status__ = "Production"

load_dotenv()


# Collect EPSS Scores
def epss_check(cve_id):

    try:
        epss_url = EPSS_URL + f"?cve={cve_id}"
        epss_response = requests.get(epss_url)
        epss_status_code = epss_response.status_code

        if epss_status_code == 200:
            if epss_response.json().get("total") > 0:
                for cve in epss_response.json().get("data"):
                    results = {"epss": float(cve.get("epss")),
                               "percentile": int(float(cve.get("percentile"))*100)}
                    return results
            else:
                return False
        else:
            print("Error connecting to EPSS")
    except requests.exceptions.ConnectionError:
        print(f"Unable to connect to EPSS, Check your Internet connection or try again")
        return None


# Check NIST NVD for the CVE
def nist_check(cve_id):

    try:
        nvd_key = os.getenv('NIST_API')
        nvd_url = NIST_BASE_URL + f"?cveId={cve_id}"
        header = {'apiKey': f'{nvd_key}'}

        # Check if API has been provided
        if nvd_key:
            nvd_response = requests.get(nvd_url, headers=header)
        else:
            nvd_response = requests.get(nvd_url)

        nvd_status_code = nvd_response.status_code

        if nvd_status_code == 200:
            cisa_kev = False
            if nvd_response.json().get("totalResults") > 0:
                for unique_cve in nvd_response.json().get("vulnerabilities"):

                    # Check if present in CISA's KEV
                    if unique_cve.get("cve").get("cisaExploitAdd"):
                        cisa_kev = True

                    # Collect CPEs
                    cpes1 = []
                    if unique_cve.get("cve").get("configurations"):
                        for config in unique_cve.get("cve").get("configurations"):
                            for node in config.get("nodes"):
                                for match in node.get("cpeMatch"):
                                    cpe_string = match.get("criteria")
                                    cpe_list = cpe_string.split(":",5)
                                    cpe_list.pop(5)
                                    cpe_string = ":".join(str(x) for x in cpe_list)
                                    cpes1.append(cpe_string)
                    
                    # Collect CVSS Data
                    if unique_cve.get("cve").get("metrics").get("cvssMetricV31"):
                        for metric in unique_cve.get("cve").get("metrics").get("cvssMetricV31"):
                            results = {"cvss_version": "CVSS 3.1",
                                       "cvss_baseScore": float(metric.get("cvssData").get("baseScore")),
                                       "cvss_severity": metric.get("cvssData").get("baseSeverity"),
                                       "cvss_av": metric.get("cvssData").get("attackVector"),
                                       "cvss_ui": metric.get("cvssData").get("userInteraction"),
                                       "cvss_priv": metric.get("cvssData").get("privilegesRequired"),
                                       "cvss_integrity": metric.get("cvssData").get("integrityImpact"),
                                       "cvss_confidentiality": metric.get("cvssData").get("confidentialityImpact"),
                                       "cisa_kev": cisa_kev, "cpes": cpes1}
                            return results
                    elif unique_cve.get("cve").get("metrics").get("cvssMetricV30"):
                        for metric in unique_cve.get("cve").get("metrics").get("cvssMetricV30"):
                            results = {"cvss_version": "CVSS 3.0",
                                       "cvss_baseScore": float(metric.get("cvssData").get("baseScore")),
                                       "cvss_severity": metric.get("cvssData").get("baseSeverity"),
                                       "cvss_av": metric.get("cvssData").get("attackVector"),
                                       "cvss_ui": metric.get("cvssData").get("userInteraction"),
                                       "cvss_priv": metric.get("cvssData").get("privilegesRequired"),
                                       "cvss_integrity": metric.get("cvssData").get("integrityImpact"),
                                       "cvss_confidentiality": metric.get("cvssData").get("confidentialityImpact"),
                                       "cisa_kev": cisa_kev, "cpes": cpes1}
                            return results
                    elif unique_cve.get("cve").get("metrics").get("cvssMetricV2"):
                        for metric in unique_cve.get("cve").get("metrics").get("cvssMetricV2"):
                            results = {"cvss_version": "CVSS 2.0",
                                       "cvss_baseScore": float(metric.get("cvssData").get("baseScore")),
                                       "cvss_severity": metric.get("cvssData").get("baseSeverity"),
                                       "cvss_av": metric.get("cvssData").get("accessVector"),
                                       "cvss_ui": metric.get("cvssData").get("authentication"),
                                       "cvss_priv": "null",
                                       "cvss_integrity": metric.get("cvssData").get("integrityImpact"),
                                       "cvss_confidentiality": metric.get("cvssData").get("confidentialityImpact"),
                                       "cisa_kev": cisa_kev, "cpes": cpes1}
                            return results
                    elif unique_cve.get("cve").get("vulnStatus") == "Awaiting Analysis":
                        print(f"{cve_id:<18}NIST Status: {unique_cve.get('cve').get('vulnStatus')}")
            else:
                print(f"{cve_id:<18}Not Found in NIST NVD.")
        else:
            print(f"{cve_id:<18}Error")
    except requests.exceptions.ConnectionError:
        print(f"Unable to connect to NIST NVD, Check your Internet connection or try again")
        return None


def colored_print(priority):
    if priority == 'Priority 1+':
        return colored(priority, 'red')
    elif priority == 'Priority 1':
        return colored(priority, 'light_red')
    elif priority == 'Priority 2':
        return colored(priority, 'light_yellow')
    elif priority == 'Priority 3':
        return colored(priority, 'yellow')
    elif priority == 'Priority 4':
        return colored(priority, 'green')


# Function manages the outputs
def print_and_write(working_file, cve_id, priority, epss, cvss_base_score, cvss_version, cvss_severity, cvss_av, cvss_ui, cvss_priv, cvss_integrity, cvss_confidentiality, cisa_kev, cpes, verbose):

    color_priority = colored_print(priority)

    if verbose:
        print(f"{cve_id:<18}{color_priority:<22}{epss:<9}{cvss_base_score:<6}{cvss_version:<10}{cvss_severity:<10}{cvss_av:<18}{cvss_ui:<10}{cvss_priv:<10}{cvss_integrity:<6}{cvss_confidentiality:<6}{cisa_kev:<10}{cpes}")
    else:
        print(f"{cve_id:<18}{color_priority:<22}")
    if working_file:
        working_file.write(f"{cve_id}\t{priority}\t{epss}\t{cvss_base_score}\t{cvss_version}\t{cvss_severity}\t{cvss_av}\t{cvss_ui}\t{cvss_priv}\t{cvss_integrity}\t{cvss_confidentiality}\t{cisa_kev}\t{cpes}\n")


# Main function
def worker(cve_id, cvss_score, epss_score, verbose_print, save_output=None):
    nist_result = nist_check(cve_id)
    epss_result = epss_check(cve_id)

    working_file = None
    if save_output:
        working_file = open(save_output, 'a')

#cvss_av, cvss_ui, cvss_integrity, cvss_confidentiality

    try:
        if nist_result.get("cisa_kev"):
            print_and_write(working_file, cve_id, 'Priority 1+', epss_result.get('epss'),
                            nist_result.get('cvss_baseScore'), nist_result.get('cvss_version'),
                            nist_result.get('cvss_severity'), nist_result.get('cvss_av'),
                            nist_result.get('cvss_ui'), nist_result.get('cvss_priv'),
                            nist_result.get('cvss_integrity'), nist_result.get('cvss_confidentiality'),
                            'TRUE', nist_result.get('cpes'), verbose_print)
        elif nist_result.get("cvss_baseScore") >= cvss_score:
            if epss_result.get("epss") >= epss_score:
                print_and_write(working_file, cve_id, 'Priority 1', epss_result.get('epss'),
                                nist_result.get('cvss_baseScore'), nist_result.get('cvss_version'),
                                nist_result.get('cvss_severity'), nist_result.get('cvss_av'),
                                nist_result.get('cvss_ui'), nist_result.get('cvss_priv'),
                                nist_result.get('cvss_integrity'), nist_result.get('cvss_confidentiality'),
                                'FALSE', nist_result.get('cpes'), verbose_print)
            else:
                print_and_write(working_file, cve_id, 'Priority 2', epss_result.get('epss'),
                                nist_result.get('cvss_baseScore'), nist_result.get('cvss_version'),
                                nist_result.get('cvss_severity'), nist_result.get('cvss_av'),
                                nist_result.get('cvss_ui'), nist_result.get('cvss_priv'),
                                nist_result.get('cvss_integrity'), nist_result.get('cvss_confidentiality'),
                                'FALSE', nist_result.get('cpes'), verbose_print)
        else:
            if epss_result.get("epss") >= epss_score:
                print_and_write(working_file, cve_id, 'Priority 3', epss_result.get('epss'),
                                nist_result.get('cvss_baseScore'), nist_result.get('cvss_version'),
                                nist_result.get('cvss_severity'), nist_result.get('cvss_av'),
                                nist_result.get('cvss_ui'), nist_result.get('cvss_priv'),
                                nist_result.get('cvss_integrity'), nist_result.get('cvss_confidentiality'),
                                'FALSE', nist_result.get('cpes'), verbose_print)
            else:
                print_and_write(working_file, cve_id, 'Priority 4', epss_result.get('epss'),
                                nist_result.get('cvss_baseScore'), nist_result.get('cvss_version'),
                                nist_result.get('cvss_severity'), nist_result.get('cvss_av'),
                                nist_result.get('cvss_ui'), nist_result.get('cvss_priv'),
                                nist_result.get('cvss_integrity'), nist_result.get('cvss_confidentiality'),
                                'FALSE', nist_result.get('cpes'), verbose_print)
    except (TypeError, AttributeError):
        pass

    if working_file:
        working_file.close()


# Function retrieves data from CVE Trends
def cve_trends():

    cve_list = []

    try:
        html = requests.get("https://cvetrends.com/api/cves/7days")
        parsed = html.json()
        if html.status_code == 200:
            for cve in parsed.get("data"):
                cve_list.append(cve.get("cve"))
        else:
            return None
    except ConnectionError:
        print(f"Unable to connect to CVE Trends, Check your Internet connection or try again")
        return None

    return cve_list

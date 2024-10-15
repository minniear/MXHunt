import argparse
import re
import asyncio
import itertools
import json
from rich.console import Console
from rich.table import Table
from rich.status import Status
from mxhunt.helper.throttledclientsession import ThrottledClientSession

console = Console()


class Checker:
    def __init__(self, session, status):
        self.session = session
        self.status = status
        self.tenantnames = []
        self.domains = []
        self.report = []
        self.mx_records = []

    async def msoldomains(self, initial_domain):
        url = "https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc"

        data = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:exm="http://schemas.microsoft.com/exchange/services/2006/messages" xmlns:ext="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:a="http://www.w3.org/2005/08/addressing" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <soap:Header>
        <a:Action soap:mustUnderstand="1">http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation</a:Action>
        <a:To soap:mustUnderstand="1">https://autodiscover-s.outlook.com/autodiscover/autodiscover.svc</a:To>
        <a:ReplyTo>
            <a:Address>http://www.w3.org/2005/08/addressing/anonymous</a:Address>
        </a:ReplyTo>
    </soap:Header>
    <soap:Body>
        <GetFederationInformationRequestMessage xmlns="http://schemas.microsoft.com/exchange/2010/Autodiscover">
            <Request>
                <Domain>{initial_domain}</Domain>
            </Request>
        </GetFederationInformationRequestMessage>
    </soap:Body>
</soap:Envelope>"""

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"http://schemas.microsoft.com/exchange/2010/Autodiscover/Autodiscover/GetFederationInformation"',
            "User-Agent": "AutodiscoverClient",
            "Accept-Encoding": "identity",
        }
        async with self.session.post(url, headers=headers, data=data) as response:

            r = re.compile(r"<Domain>([^<>/]*)</Domain>", re.I)
            domains = list(set(r.findall(await response.text())))

            for domain in domains:
                if domain.lower().endswith(".onmicrosoft.com"):
                    self.tenantnames.append(domain.split(".")[0])

            if domains:
                self.domains.extend(domains)
                tasks = await asyncio.gather(
                    *[self.get_mx(domain) for domain in domains]
                )

                self.report.append(
                    {"initial_domain": initial_domain, "tenant_domains": []}
                )
                for domain, result in zip(domains, tasks):
                    self.report[-1]["tenant_domains"].append(
                        {"domain": domain, "records": result}
                    )
        return domains

    async def get_mx(self, tenant_domain):
        try:
            records = []
            self.status.update(f"Checking MX records for {tenant_domain}")
            async with self.session.get(
                f"https://dns.google/resolve?name={tenant_domain}&type=MX"
            ) as response:
                json_response = await response.json()
                for record in json_response["Answer"]:
                    self.mx_records.append(record["data"].split()[1])
                    records.append(
                        dict(
                            priority=record["data"].split()[0],
                            mx=record["data"].split()[1],
                        )
                    )
                return records

        except:
            return None

    def print_mx_records(self):
        table = Table(show_edge=False)
        table.add_column(header="MX Record", justify="left", header_style="bold")
        for record in sorted(set(self.mx_records)):
            table.add_row(record[:-1])
        console.print(table)


def parse_args():
    parser = argparse.ArgumentParser(description="Hunt for mail servers using MSOL")
    parser.add_argument(
        "-r",
        "--rate",
        help="Rate limit of concurrent connections (default: 10)",
        default=10,
        type=int,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help="Quiet mode, do not output mail servers",
        action="store_true",
    )
    input = parser.add_argument_group(title="Input Options")
    group = input.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--domain", help="Domain to check")
    group.add_argument("-f", "--file", help="A file with domains to check")
    output = parser.add_argument_group(title="Output Options")
    output.add_argument(
        "-o",
        "--output",
        help="Report output base name (default: mx_report)",
        default="mx_report",
    )

    return parser.parse_args()


async def main():
    args = parse_args()
    rate = args.rate
    file = args.file
    domain = args.domain
    output_base = args.output
    quiet = args.quiet

    with Status(f"Checking domain{'' if domain else 's'}") as status:
        async with ThrottledClientSession(rate_limit=rate) as session:
            checker = Checker(session, status)

            if domain:
                msol_domains = await checker.msoldomains(domain)

            else:
                with open(file) as f:
                    domains = f.read().splitlines()

                tasks = await asyncio.gather(
                    *[checker.msoldomains(domain) for domain in domains]
                )

                merged_domains = list(itertools.chain(*tasks))
                msol_domains = sorted(set(merged_domains))

            status.stop()
            console.print(f"[cyan]Writing report to {output_base}.json[/cyan]")
            with open(f"{output_base}.json", "w") as f:
                json.dump(checker.report, f, indent=4)

            if not quiet:
                checker.print_mx_records()


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()

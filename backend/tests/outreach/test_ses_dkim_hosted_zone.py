"""AWS SES's Easy DKIM CNAME hosted-zone suffix varies by Region and cell — it
is NOT always "dkim.amazonses.com". For newer opt-in Regions (e.g. ap-south-2)
AWS's GetEmailIdentity response returns the actual required suffix in a
SigningHostedZone field. Our code previously hardcoded the legacy universal
suffix, which told operators to publish the wrong CNAME target — DKIM
verification then stays FAILED forever regardless of what they add to DNS.
https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html
"""
from unittest.mock import MagicMock, patch

from app.services.outreach.email_transport import ExecutiveIdentity, _identity_details_sync


def _identity() -> ExecutiveIdentity:
    return ExecutiveIdentity(name="Joseph David", title="Executive Director", email="joseph.david@aliyarsolutions.com")


class TestDkimHostedZone:
    def test_uses_signing_hosted_zone_from_aws_response(self):
        """Region-qualified hosted zone (ap-south-2) must be used verbatim, not
        replaced with the legacy universal suffix."""
        mock_client = MagicMock()
        mock_client.get_email_identity.return_value = {
            "IdentityType": "DOMAIN",
            "VerificationStatus": "PENDING",
            "VerifiedForSendingStatus": False,
            "DkimAttributes": {
                "Status": "PENDING",
                "Tokens": ["eyakcz2w2tbeu7fbljqjn2gfgmcxt2nv"],
                "SigningHostedZone": "dkim.ap-south-2.amazonses.com",
            },
        }
        with patch("app.services.outreach.email_transport._sesv2_client", return_value=mock_client):
            details = _identity_details_sync(_identity())

        domain_entry = next(d for d in details if d["identity"] == "aliyarsolutions.com")
        assert domain_entry["dkim_signing_hosted_zone"] == "dkim.ap-south-2.amazonses.com"
        assert domain_entry["dkim_records"] == [
            {
                "type": "CNAME",
                "name": "eyakcz2w2tbeu7fbljqjn2gfgmcxt2nv._domainkey.aliyarsolutions.com",
                "value": "eyakcz2w2tbeu7fbljqjn2gfgmcxt2nv.dkim.ap-south-2.amazonses.com",
            }
        ]

    def test_falls_back_to_legacy_suffix_when_field_absent(self):
        """Older regions/SDK responses without SigningHostedZone still work."""
        mock_client = MagicMock()
        mock_client.get_email_identity.return_value = {
            "IdentityType": "DOMAIN",
            "VerificationStatus": "SUCCESS",
            "VerifiedForSendingStatus": True,
            "DkimAttributes": {
                "Status": "SUCCESS",
                "Tokens": ["abc123"],
            },
        }
        with patch("app.services.outreach.email_transport._sesv2_client", return_value=mock_client):
            details = _identity_details_sync(_identity())

        domain_entry = next(d for d in details if d["identity"] == "aliyarsolutions.com")
        assert domain_entry["dkim_signing_hosted_zone"] == "dkim.amazonses.com"
        assert domain_entry["dkim_records"][0]["value"] == "abc123.dkim.amazonses.com"

    def test_cell_prefixed_hosted_zone_also_passes_through(self):
        """AWS docs show some cells use a form like {token}.{cell}.dkim.{region}.amazonses.com —
        whatever AWS returns must be used verbatim, never re-derived."""
        mock_client = MagicMock()
        mock_client.get_email_identity.return_value = {
            "IdentityType": "DOMAIN",
            "VerificationStatus": "PENDING",
            "VerifiedForSendingStatus": False,
            "DkimAttributes": {
                "Status": "PENDING",
                "Tokens": ["tok1"],
                "SigningHostedZone": "a31d.dkim.us-west-2.amazonses.com",
            },
        }
        with patch("app.services.outreach.email_transport._sesv2_client", return_value=mock_client):
            details = _identity_details_sync(_identity())

        domain_entry = next(d for d in details if d["identity"] == "aliyarsolutions.com")
        assert domain_entry["dkim_records"][0]["value"] == "tok1.a31d.dkim.us-west-2.amazonses.com"

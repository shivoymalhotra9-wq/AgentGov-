# Ticket: ITEM-001 - Create a private VCN for internal workloads
# Drafted by: infra-drafter
# Status: DRAFTED - not audited, not deployed
terraform {
  required_providers {
    oci = {
      source = "oracle/oci"
    }
  }
}

resource "oci_core_vcn" "internal_vcn" {
  compartment_id = "ocid1.compartment.example"
  cidr_block     = "10.0.0.0/16"
  display_name   = "internal-vcn"
  dns_label      = "internalvcn"
}

resource "oci_core_subnet" "private_subnet" {
  compartment_id             = "ocid1.compartment.example"
  vcn_id                     = oci_core_vcn.internal_vcn.id
  cidr_block                 = "10.0.1.0/24"
  display_name               = "private-subnet"
  prohibit_public_ip_on_vnic = true
}

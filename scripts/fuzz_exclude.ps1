#!usr/bin/env pwsh
param ([int]$i = 1, [string]$clean = "false")
$clean_txt = ""
if ($clean.ToLower() -eq "true") {
    $clean_txt = "--clean"
}
python -m fuzze --destination ../addons/fuzze --name main_flow_tour --source ../../odoo/odoo/addons/test_main_flows/static/tests/tours/main_flow.js --strategy index --exclude 1 2 12 13 14 26 6 10 24 27 --iterations $i $clean_txt
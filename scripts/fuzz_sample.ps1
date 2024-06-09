#!usr/bin/env pwsh
param ([int]$i = 1, [string]$clean = "false")
$clean_txt = ""
if ($clean.ToLower() -eq "true") {
    $clean_txt = "--clean"
}
python -m fuzze --destination ../addons/fuzze --name main_flow_tour --source ../../odoo/odoo/addons/test_main_flows/static/tests/tours/main_flow.js --strategy sample --sampleStrategy.include 0 3 4 5 7 8 9 11 15 16 17 18 19 20 21 22 23 25 28 29 30 31 32 33 34 --k 10 --iterations $i $clean_txt
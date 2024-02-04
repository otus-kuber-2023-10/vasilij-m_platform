#!/bin/bash

CHARTS=("$@")
CHARTS_DIR=./kubernetes-templating
CHARTS_ARCHIVE_DIR=/tmp
REGISTRY=harbor.prod.vasilijm.ru/helm
REGISTRY_USER=admin
REGISTRY_PASSWORD=Harbor12345

helm registry login https://$REGISTRY --username=$REGISTRY_USER --password=$REGISTRY_PASSWORD

for chart in ${CHARTS[*]}
do
    chart_version=$(awk -F ' ' '/^version:/ {print $2}' $CHARTS_DIR/$chart/Chart.yaml)
    helm package --version $chart_version --destination $CHARTS_ARCHIVE_DIR $CHARTS_DIR/$chart
    helm push $CHARTS_ARCHIVE_DIR/$chart-$chart_version.tgz oci://$REGISTRY
done

In this tutorial you learn how to build a demo dashboard application on [Google Cloud Platform](https://cloud.google.com/) by using the [Bokeh](http://bokeh.pydata.org/en/latest/) library to visualize data from publicly available [Google BigQuery](https://cloud.google.com/bigquery/) datasets. You also learn how to deploy this application with both security and scalability in mind.

Please refer to the related article for all the steps to follow in this tutorial: https://cloud.google.com/solutions/bokeh-and-bigquery-dashboards

Contents of this repository:

* `dashboard`: Python code to generate the dashboard using the Bokeh library. This folder also contains a `Dockerfile` in case you wish to build the container.
* `kubernetes`: Configuration files to deploy the application using [Kubernetes](https://kubernetes.io/).

## Updating app (just the bokeh service)
#### make sure PROJECT_ID is exported
`export PROJECT_ID="$(gcloud config get-value project -q)"`

#### Build new docker image (for bokeh service)
`docker build -t gcr.io/${PROJECT_ID}/bokeh:v[version-number] .`

### Upload the container image
`gcloud docker -- push gcr.io/${PROJECT_ID}/bokeh:v[version-number]`

#### Set image
`kubectl set image deployment/bokeh bokeh=gcr.io/${PROJECT_ID}/bokeh:v[version-number]`

### when your image invariably fails:
`kubectl logs [pod id]`

#check path

#### Add user

`gcloud projects add-iam-policy-binding $PROJECT_ID \
  --role roles/iap.httpsResourceAccessor \
  --member user:[EMAIL]
`
# TODO:

1.  Separate out tables into separate modules.
2.  Integrate MSC data queries (integrate options for parameters?  temp, precip, etc.)
3.  Implement frequency Analysis based on selection (or implement generalized approach, i.e. k-fold cross-validation?)
4.  Frequency analysis results comparison based on inclusion / exclusion of flagged data (incl. metrics).  
        -i.e. on a large scale, how does inclusion/exclusion of flagged data affect results?
5.  Anomaly detection based on comparison of stage/flow and regional precip/temperature data.  icing?
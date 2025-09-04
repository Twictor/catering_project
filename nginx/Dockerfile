# Use the official lightweight Nginx image
FROM nginx:alpine

# Remove the default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy our configuration file into the container
COPY nginx.conf /etc/nginx/conf.d/

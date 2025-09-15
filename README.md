I have been working on a Full stack app with a FastAPI / Python backend and 2 seperate react front end. In the app I was thikning that I was going to be submitting a flickr image (or even a set / album) URL and the app would be able to show the images. It didn't quite dawn on me that the URLs I was submitting were actually URL to the "page" of the flickr image (or the set / album of images) and not the image URL itself. I could manually get the static image URL but it would be a few more additional manual steps and I was wondering if there could be a better way of implementing it. I am not really looking for a solution specifically for the app I have been working on but am not wondering in a general sense.

Definitely leaning to the flickr api approach but this app is but one of the apps that I am currently working on where I need something like this and am thinking that it would be a good idea to develop a independnt app / api that I could use with these and maybe even future apps.

Deployment Considerations
Given your AWS/GCP background, you could deploy this as:

ECS/Cloud Run: Container-based deployment
Lambda/Cloud Functions: For lighter usage
EKS/GKE: If you need serious scaling
Simple EC2/Compute Engine: With Docker Compose

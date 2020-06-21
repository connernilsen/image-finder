# Similar Image Detector

## Overview
This is a Python program for detecting similar images within a given repository.
It is mean to be used over time, however, a full db-clean should not be too costly
(as long as you don't have too many images) so it is currently being performed 
on schema updates. 

### Comparison methods
The current plan is to employ three main methods of detecting similarity in images. In 
each case, the image is scaled down and grayscaled.
- Average Hashing
  - Takes the average color of the image and determines if 
  each pixel is above or below the average color. A bit-array representation of that is 
  is converted into a hex representation. The fastest algorithm, but the least precise since
  a smaller image is used in reduction.
- Perceptual Hashing
  - Uses a [discrete cosine transform](https://en.wikipedia.org/wiki/Discrete_cosine_transform)
  to distill the lowest frequency values in an image to determine a fingerprint, which is then
  hashed. Similar to the average hash, but to an extreme. The slowest, but most precise.
- Difference Hashing
  - Creates a hash based on the color gradient across an image. Each color in a row is
  compared to the color directly next to it, and bit values represent a positive or 
  negative change. A faster algorithm with high precision (not as fast as average,
  but not as precise as perceptual -- a good in-between).
  
Comparisons are done between the hashes using a 
[Hamming Distance](https://en.wikipedia.org/wiki/Hamming_distance).

## Roadmap
- [x] Implement hashing algorithms
  - [x] Asynchronously calculate information for images
  - [ ] Asynchronously compare images
- [ ] Compare image and determine what to do when close matches are found
- [ ] Store image information in db to reduce calculation time
- [ ] Implement method to ignore similar images on future runs
- [ ] Allow user to specify tolerance
- [ ] Add image selection to randomly select images for use 
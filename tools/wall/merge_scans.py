import sys, json, numpy as np, cv2
a_path, b_path, out = sys.argv[1:4]
A = cv2.imread(a_path, cv2.IMREAD_UNCHANGED); B = cv2.imread(b_path, cv2.IMREAD_UNCHANGED)
def gray(I):
    g = cv2.cvtColor(I[:, :, :3], cv2.COLOR_BGR2GRAY); g[I[:, :, 3] == 0] = 0; return g
sift = cv2.SIFT_create(8000)
ka, da = sift.detectAndCompute(gray(A), (A[:, :, 3] > 0).astype(np.uint8))
kb, db = sift.detectAndCompute(gray(B), (B[:, :, 3] > 0).astype(np.uint8))
m = cv2.BFMatcher().knnMatch(db, da, k=2)
good = [x for x, y in m if x.distance < 0.7 * y.distance]
src = np.float32([kb[g.queryIdx].pt for g in good]); dst = np.float32([ka[g.trainIdx].pt for g in good])
M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0, maxIters=5000)
s = float(np.hypot(M[0, 0], M[1, 0])); rot = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
print(json.dumps(dict(matches=len(good), inliers=int(inl.sum()), scale=round(s, 4), rot_deg=round(rot, 2), tx=round(float(M[0, 2]), 1), ty=round(float(M[1, 2]), 1))))
# canvas in A's frame, grown to hold B
h, w = A.shape[:2]; hb, wb = B.shape[:2]
corners = cv2.transform(np.float32([[[0, 0], [wb, 0], [0, hb], [wb, hb]]]), M)[0]
x0 = int(np.floor(min(0, corners[:, 0].min()))); y0 = int(np.floor(min(0, corners[:, 1].min())))
x1 = int(np.ceil(max(w, corners[:, 0].max()))); y1 = int(np.ceil(max(h, corners[:, 1].max())))
T = np.array([[1, 0, -x0], [0, 1, -y0]], np.float32)
W, H = x1 - x0, y1 - y0
Ac = cv2.warpAffine(A, T, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
M2 = M.copy(); M2[:, 2] -= [x0, y0]
Bw = cv2.warpAffine(B, M2, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
fill = (Ac[:, :, 3] == 0) & (Bw[:, :, 3] > 0)
C = Ac.copy(); C[fill] = Bw[fill]
cv2.imwrite(out, C)
both = (Ac[:, :, 3] > 0) & (Bw[:, :, 3] > 0)
# agreement where both have data: mean abs difference of grey
d = np.abs(cv2.cvtColor(Ac[:, :, :3], cv2.COLOR_BGR2GRAY).astype(int) - cv2.cvtColor(Bw[:, :, :3], cv2.COLOR_BGR2GRAY).astype(int))[both]
mask = np.zeros((H, W, 3), np.uint8); mask[Ac[:, :, 3] > 0] = (90, 90, 90); mask[fill] = (0, 200, 255)
cv2.imwrite(out.replace('.png', '_newpixels.png'), mask)
print(json.dumps(dict(canvas=[W, H], offset=[x0, y0], new_px=int(fill.sum()), overlap_px=int(both.sum()), overlap_mean_grey_diff=round(float(d.mean()), 1),
                      coverage_before=round(float((Ac[:, :, 3] > 0).mean()), 3), coverage_after=round(float((C[:, :, 3] > 0).mean()), 3))))

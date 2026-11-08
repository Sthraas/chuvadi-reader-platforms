// Test tool only. Launches a command, polls the X root window, reports ms since exec:
//  map: first poll where the screen differs from before launch
//  content: first poll where the changed pixels hold > 200 distinct colours (smoke test's rule)
//  settled: last change before the screen stays identical for STABLE_MS
// The bottom MASK rows (status-bar clock, ticks every second) are ignored.
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>
#define MASK 40
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
static unsigned long *base; static int W,H;
static unsigned long long scan(XImage*im,int*colours,int keep){
  unsigned long long h=1469598103934665603ULL; static unsigned char seen[(1<<15)/8]; memset(seen,0,sizeof seen); int n=0,i=0;
  for(int y=0;y<H-MASK;y+=2)for(int x=0;x<W;x+=2,i++){unsigned long p=XGetPixel(im,x,y)&0xffffff;
    if(keep){base[i]=p;continue;}
    h=(h^p)*1099511628211ULL;
    if(p!=base[i]){unsigned q=((p>>3)&0x1f)|(((p>>11)&0x1f)<<5)|(((p>>19)&0x1f)<<10); if(!(seen[q>>3]&(1<<(q&7)))){seen[q>>3]|=1<<(q&7);n++;}}}
  *colours=n; return h;}
int main(int c,char**v){
  int timeout=atoi(v[1]),stable=atoi(v[2]); char**cmd=v+4;
  Display*d=XOpenDisplay(NULL); if(!d){fprintf(stderr,"no display\n");return 2;}
  Window r=DefaultRootWindow(d); XWindowAttributes a; XGetWindowAttributes(d,r,&a); W=a.width;H=a.height;
  base=calloc((W/2+1)*(H/2+1),sizeof *base);
  int col; XImage*im=XGetImage(d,r,0,0,W,H,AllPlanes,ZPixmap); scan(im,&col,1); unsigned long long b=scan(im,&col,0); XDestroyImage(im);
  double t0=now(); pid_t pid=fork(); if(!pid){execvp(cmd[0],cmd);_exit(127);}
  double tmap=-1,tcontent=-1,tlast=0,lastpoll=0,maxgap=0; unsigned long long prev=b; int polls=0;
  while(1){ if(now()-t0>timeout)break;
    im=XGetImage(d,r,0,0,W,H,AllPlanes,ZPixmap); unsigned long long h=scan(im,&col,0); XDestroyImage(im); polls++;
    double tt=now()-t0; if(lastpoll>0&&tt-lastpoll>maxgap)maxgap=tt-lastpoll; lastpoll=tt;
    if(h!=b&&tmap<0)tmap=tt;
    if(col>200&&tcontent<0)tcontent=tt;
    if(h!=prev){tlast=tt;prev=h;}
    if(tcontent>0&&tt-tlast>stable)break;
    usleep(8000);
    int st; if(waitpid(pid,&st,WNOHANG)==pid){fprintf(stderr,"app exited early\n");break;}
  }
  printf("map=%.0f content=%.0f settled=%.0f colours=%d polls=%d maxgap=%.0f\n",tmap,tcontent,tlast,col,polls,maxgap);
  fflush(stdout);
  kill(pid,SIGTERM); for(int i=0;i<30&&waitpid(pid,NULL,WNOHANG)==0;i++)usleep(100000);
  if(waitpid(pid,NULL,WNOHANG)==0){fprintf(stderr,"SIGTERM ignored for 3 s, SIGKILL\n");kill(pid,SIGKILL);waitpid(pid,NULL,0);}
  return 0;}

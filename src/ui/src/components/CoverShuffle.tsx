import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Track } from './Types';

const CoverShuffle: React.FC<{ playlistId: string }> = ({ playlistId }) => {
    const [covers, setCovers] = useState<Track[]>([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [isAnimating, setIsAnimating] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const scrollTimeout = useRef<NodeJS.Timeout>();

    const fetchCovers = async (playlistId: string): Promise<Track[]> => {
        const token = localStorage.getItem('spotifyToken');
        if (!token) {
            console.error('No token found');
            return [];
        }
        const endpoint = `http://localhost/api/playlist/${playlistId}`;
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            const data = await response.json();
            return data.tracks.items.map((item: any) => ({
                id: item.track.id,
                name: item.track.name,
                album: item.track.album.name,
                artists: item.track.artists.map((artist: any) => artist.name),
                coverUrl: item.track.album.images[0]?.url,
            }));
        } catch (error) {
            console.error(error);
            return [];
        }
    };

    const handleWheel = useCallback((e: WheelEvent) => {
        e.preventDefault();
        
        if (scrollTimeout.current) {
            clearTimeout(scrollTimeout.current);
        }

        scrollTimeout.current = setTimeout(() => {
            setIsAnimating(false);
        }, 1500);

        setIsAnimating(true);
        
        const delta = e.deltaX || e.deltaY;
        setSelectedIndex(prev => {
            const next = prev + (delta > 0 ? 1 : -1);
            return Math.max(0, Math.min(covers.length - 1, next));
        });
    }, [covers.length]);

    useEffect(() => {
        const loadCovers = async () => {
            const covers = await fetchCovers(playlistId);
            setCovers(covers);
        };
        loadCovers();
    }, [playlistId]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        container.addEventListener('wheel', handleWheel, { passive: false });
        
        return () => {
            container.removeEventListener('wheel', handleWheel);
            if (scrollTimeout.current) {
                clearTimeout(scrollTimeout.current);
            }
        };
    }, [handleWheel]);

    useEffect(() => {
        const handleKeyPress = (e: KeyboardEvent) => {
            if (isAnimating) return;
            
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                setIsAnimating(true);
                setTimeout(() => setIsAnimating(false), 500);
                
                setSelectedIndex(prev => {
                    const next = prev + (e.key === 'ArrowLeft' ? -1 : 1);
                    return Math.max(0, Math.min(covers.length - 1, next));
                });
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        return () => window.removeEventListener('keydown', handleKeyPress);
    }, [covers.length, isAnimating]);

    return (
        <div className="w-11/12 mx-auto mt-8 h-screen">
            <div className="relative flex items-center justify-center w-3/4 mx-auto h-1/2"
                 ref={containerRef}
                 style={{
                     perspective: '2000px',
                     perspectiveOrigin: '50% 50%'
                 }}>
                {/* Enhanced reflection surface with smoother gradient */}
                <div className="absolute bottom-0 w-full  via-gray-900/50 to-transparent" />
                
                {/* Covers container with improved transitions */}
                <div className="relative w-full h-96 flex items-center justify-center transform-gpu"
                     style={{
                         transformStyle: 'preserve-3d'
                     }}>
                    {covers.map((cover, index) => {
                        const offset = index - selectedIndex;
                        const isSelected = index === selectedIndex;
                        const zOffset = Math.abs(offset) * 100;
                        
                        const xTransform = offset * 200;
                        const zTransform = isSelected ? 200 : -zOffset;
                        const yRotation = offset * (offset > 0 ? -70 : 70);
                        const scale = isSelected ? 1 : 0.7;
                        const opacity = Math.max(0.2, 1 - Math.abs(offset) * 0.3);

                        return (
                            <div
                                key={cover.id}
                                className={`absolute cursor-pointer transform-gpu 
                                          transition-all duration-300 ease-out
                                          ${isAnimating ? 'duration-700' : 'duration-300'}`}
                                style={{
                                    width: '300px',
                                    height: '300px',
                                    left: '50%',
                                    top: '50%',
                                    transform: `
                                        translate(-50%, -50%)
                                        translateX(${xTransform}px)
                                        translateZ(${zTransform}px)
                                        rotateY(${yRotation}deg)
                                        scale(${scale})
                                    `,
                                    transformStyle: 'preserve-3d',
                                    zIndex: isSelected ? 10 : 10 - Math.abs(offset),
                                    opacity
                                }}
                                onClick={() => {
                                    if (!isAnimating && !isSelected) {
                                        setIsAnimating(true);
                                        setTimeout(() => setIsAnimating(false), 700);
                                        setSelectedIndex(index);
                                    }
                                }}
                            >
                                <div className="relative w-full h-full group">
                                    {/* Main image with enhanced hover effects */}
                                    <div className="w-full h-full transition-transform duration-500 ease-out 
                                                transform-gpu group-hover:scale-105">
                                        <img
                                            src={cover.coverUrl}
                                            alt={cover.name}
                                            className="w-full h-full object-cover rounded-2xl shadow-2xl
                                                     transition-shadow duration-500 ease-out
                                                     group-hover:shadow-xl group-hover:shadow-black/30"
                                            style={{
                                                backfaceVisibility: 'hidden',
                                                WebkitBackfaceVisibility: 'hidden'
                                            }}
                                        />
                                    </div>
                                    
                                    {/* Enhanced reflection effect */}
                                    <div 
                                        className="absolute top-full left-0 w-full h-full 
                                                 transform-gpu origin-top opacity-10
                                                 transition-all duration-700 ease-out
                                                 group-hover:translate-y-6"
                                    >
                                        <img
                                            src={cover.coverUrl}
                                            alt=""
                                            className="w-full h-full object-cover rounded-lg 
                                                     transform-gpu scale-y-100 rotate-180
                                                     transition-transform duration-700 ease-out"
                                        />
                                    </div>

                                    {/* Enhanced info overlay for selected cover */}
                                    {isSelected && (
                                        <div 
                                            className="absolute bottom-0 left-0 right-0 
                                                     bg-black/30 backdrop-blur-sm
                                                     mx-4 mb-4 p-4 opacity-0 rounded-xl
                                                     transform-gpu translate-y-2
                                                     transition-all duration-500 ease-out
                                                     group-hover:opacity-100 group-hover:translate-y-0"
                                        >
                                            <h3 className="text-white text-lg font-bold truncate">{cover.name}</h3>
                                            <p className="text-gray-200 text-sm truncate">{cover.artists.join(', ')}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Enhanced navigation controls */}
                <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex gap-4 z-50">
                    <button
                        onClick={() => {
                            if (!isAnimating && selectedIndex > 0) {
                                setIsAnimating(true);
                                setTimeout(() => setIsAnimating(false), 700);
                                setSelectedIndex(prev => prev - 1);
                            }
                        }}
                        className="rounded-full bg-white/10 backdrop-blur-md
                                 transition-all duration-300 ease-out
                                 hover:scale-110 h-[48px] w-[48px]
                                 disabled:opacity-50 disabled:cursor-not-allowed
                                 disabled:hover:scale-100"
                        disabled={isAnimating || selectedIndex === 0}
                    >
                        <span className="text-white text-xl">←</span>
                    </button>
                    <button
                        onClick={() => {
                            if (!isAnimating && selectedIndex < covers.length - 1) {
                                setIsAnimating(true);
                                setTimeout(() => setIsAnimating(false), 700);
                                setSelectedIndex(prev => prev + 1);
                            }
                        }}
                        className="rounded-full bg-white/10 backdrop-blur-md
                                 transition-all duration-300 ease-out
                                 hover:scale-110 h-[48px] w-[48px]
                                 disabled:opacity-50 disabled:cursor-not-allowed
                                 disabled:hover:scale-100"
                        disabled={isAnimating || selectedIndex === covers.length - 1}
                    >
                        <span className="text-white text-xl">→</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CoverShuffle;
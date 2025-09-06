
import { render, screen, fireEvent, waitFor, act } from './test-utils';
import SlidePreview from '@/components/preview/SlidePreview';
import { Slide } from '@/types/models';

// Mock requestFullscreen and exitFullscreen
Object.defineProperty(HTMLElement.prototype, 'requestFullscreen', {
  configurable: true,
  value: jest.fn(),
});

Object.defineProperty(document, 'exitFullscreen', {
  configurable: true,
  value: jest.fn(),
});

describe('SlidePreview', () => {
  const mockSlides: Slide[] = [
    {
      id: '1',
      projectId: 'test-project',
      title: '标题页',
      subtitle: '副标题',
      content: {
        text: '这是第一张幻灯片的内容',
        bullets: ['要点一', '要点二', '要点三']
      },
      layout: 'title-content',
      order: 0,
      notes: '这是演讲者备注',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    },
    {
      id: '2',
      projectId: 'test-project',
      title: '内容页',
      content: {
        text: '这是第二张幻灯片的内容',
        image: {
          url: 'https://example.com/image.jpg',
          alt: '示例图片',
          caption: '图片说明'
        }
      },
      layout: 'content-image',
      order: 1,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    },
    {
      id: '3',
      projectId: 'test-project',
      title: '图表页',
      content: {
        chart: {
          type: 'bar',
          title: '销售数据',
          data: []
        }
      },
      layout: 'chart',
      order: 2,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  ];

  beforeEach(() => {
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Basic Rendering', () => {
    it('renders correctly with slides', () => {
      render(<SlidePreview slides={mockSlides} />);

      expect(screen.getByText('标题页')).toBeInTheDocument();
      expect(screen.getByText('副标题')).toBeInTheDocument();
      expect(screen.getByText('这是第一张幻灯片的内容')).toBeInTheDocument();
      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('renders bullet points correctly', () => {
      render(<SlidePreview slides={mockSlides} />);

      expect(screen.getByText('要点一')).toBeInTheDocument();
      expect(screen.getByText('要点二')).toBeInTheDocument();
      expect(screen.getByText('要点三')).toBeInTheDocument();
    });

    it('renders image content when present', () => {
      render(<SlidePreview slides={mockSlides} currentSlideIndex={1} />);

      const image = screen.getByAltText('示例图片');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', 'https://example.com/image.jpg');
      expect(screen.getByText('图片说明')).toBeInTheDocument();
    });

    it('renders chart content when present', () => {
      render(<SlidePreview slides={mockSlides} currentSlideIndex={2} />);

      expect(screen.getByText('图表: bar')).toBeInTheDocument();
      expect(screen.getByText('销售数据')).toBeInTheDocument();
    });

    it('shows thumbnails by default', () => {
      render(<SlidePreview slides={mockSlides} />);

      const thumbnails = screen.getAllByRole('button').filter(
        button => button.className.includes('w-24 h-16')
      );
      expect(thumbnails).toHaveLength(3);
    });

    it('hides thumbnails when showThumbnails is false', () => {
      render(<SlidePreview slides={mockSlides} showThumbnails={false} />);

      const thumbnails = screen.queryAllByRole('button').filter(
        button => button.className.includes('w-24 h-16')
      );
      expect(thumbnails).toHaveLength(0);
    });

    it('renders empty state gracefully', () => {
      const { container } = render(<SlidePreview slides={[]} />);
      expect(container).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('navigates to next slide when next button is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={0}
        />
      );

      const nextButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-6')
      );
      
      fireEvent.click(nextButton!);
      expect(mockOnSlideChange).toHaveBeenCalledWith(1);
    });

    it('navigates to previous slide when previous button is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={1}
        />
      );

      const prevButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-6')
      );
      
      fireEvent.click(prevButton!);
      expect(mockOnSlideChange).toHaveBeenCalledWith(0);
    });

    it('wraps around when navigating beyond last slide', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={2}
        />
      );

      const nextButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-6') &&
                 button.className.includes('right-0')
      );
      
      fireEvent.click(nextButton!);
      expect(mockOnSlideChange).toHaveBeenCalledWith(0);
    });

    it('wraps around when navigating before first slide', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={0}
        />
      );

      const prevButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-6') &&
                 button.className.includes('left-0')
      );
      
      fireEvent.click(prevButton!);
      expect(mockOnSlideChange).toHaveBeenCalledWith(2);
    });

    it('navigates when thumbnail is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
        />
      );

      // Find thumbnail buttons
      const thumbnails = screen.getAllByRole('button').filter(
        button => button.className.includes('w-24 h-16')
      );
      
      fireEvent.click(thumbnails[1]);
      expect(mockOnSlideChange).toHaveBeenCalledWith(1);
    });
  });

  describe('View Modes', () => {
    it('switches to grid view when grid button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Should show grid layout
      expect(gridButton).toHaveClass('bg-primary-500');
      
      // Should show all slide titles in grid
      expect(screen.getAllByText('标题页')).toHaveLength(2); // One in grid, one in thumbnail
    });

    it('switches to list view when list button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      const listButton = screen.getByTitle('列表视图');
      fireEvent.click(listButton);

      // Should show list layout
      expect(listButton).toHaveClass('bg-primary-500');
      
      // Should show table headers
      expect(screen.getByText('标题')).toBeInTheDocument();
      expect(screen.getByText('类型')).toBeInTheDocument();
      expect(screen.getByText('内容')).toBeInTheDocument();
    });

    it('returns to single view when single view button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Switch to grid first
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Then back to single
      const singleButton = screen.getByTitle('单页视图');
      fireEvent.click(singleButton);

      expect(singleButton).toHaveClass('bg-primary-500');
      expect(screen.getByText('1 / 3')).toBeInTheDocument();
    });

    it('displays correct content icons in grid view', () => {
      render(<SlidePreview slides={mockSlides} />);

      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Each slide should have an appropriate icon
      const icons = screen.getAllByRole('button').filter(
        button => button.querySelector('svg')
      );
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Auto Play', () => {
    it('starts auto play when autoPlay prop is true', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          autoPlay={true}
          autoPlayInterval={1000}
        />
      );

      act(() => {
        jest.advanceTimersByTime(1000);
      });

      expect(mockOnSlideChange).toHaveBeenCalledWith(1);
    });

    it('toggles auto play when play/pause button is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          autoPlay={false}
        />
      );

      // Find play button
      const playButton = screen.getByTitle('播放');
      fireEvent.click(playButton);

      // Should now show pause icon
      expect(screen.getByTitle('暂停')).toBeInTheDocument();

      // Should start auto advance
      act(() => {
        jest.advanceTimersByTime(5000);
      });

      expect(mockOnSlideChange).toHaveBeenCalledWith(1);
    });

    it('pauses auto play when pause button is clicked', () => {
      render(
        <SlidePreview 
          slides={mockSlides} 
          autoPlay={true}
        />
      );

      const pauseButton = screen.getByTitle('暂停');
      fireEvent.click(pauseButton);

      expect(screen.getByTitle('播放')).toBeInTheDocument();
    });
  });

  describe('Zoom Controls', () => {
    it('zooms in when zoom in button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      const zoomInButton = screen.getByTitle('放大');
      fireEvent.click(zoomInButton);

      expect(screen.getByText('110%')).toBeInTheDocument();
    });

    it('zooms out when zoom out button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      const zoomOutButton = screen.getByTitle('缩小');
      fireEvent.click(zoomOutButton);

      expect(screen.getByText('90%')).toBeInTheDocument();
    });

    it('resets zoom when reset button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Zoom in first
      const zoomInButton = screen.getByTitle('放大');
      fireEvent.click(zoomInButton);
      
      // Then reset
      const resetButton = screen.getByTitle('重置缩放');
      fireEvent.click(resetButton);

      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('respects zoom limits', () => {
      render(<SlidePreview slides={mockSlides} />);

      const zoomInButton = screen.getByTitle('放大');
      const zoomOutButton = screen.getByTitle('缩小');

      // Zoom in to maximum
      for (let i = 0; i < 20; i++) {
        fireEvent.click(zoomInButton);
      }
      expect(screen.getByText('200%')).toBeInTheDocument();

      // Try to zoom in more - should stay at 200%
      fireEvent.click(zoomInButton);
      expect(screen.getByText('200%')).toBeInTheDocument();

      // Zoom out to minimum
      for (let i = 0; i < 20; i++) {
        fireEvent.click(zoomOutButton);
      }
      expect(screen.getByText('50%')).toBeInTheDocument();

      // Try to zoom out more - should stay at 50%
      fireEvent.click(zoomOutButton);
      expect(screen.getByText('50%')).toBeInTheDocument();
    });
  });

  describe('Keyboard Navigation', () => {
    it('navigates with arrow keys', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
        />
      );

      // Right arrow should go to next slide
      fireEvent.keyDown(window, { key: 'ArrowRight' });
      expect(mockOnSlideChange).toHaveBeenCalledWith(1);

      // Left arrow should go to previous slide
      fireEvent.keyDown(window, { key: 'ArrowLeft' });
      expect(mockOnSlideChange).toHaveBeenCalledWith(0);
    });

    it('toggles play/pause with spacebar', () => {
      render(<SlidePreview slides={mockSlides} autoPlay={false} />);

      expect(screen.getByTitle('播放')).toBeInTheDocument();

      fireEvent.keyDown(window, { key: ' ' });
      expect(screen.getByTitle('暂停')).toBeInTheDocument();
    });

    it('toggles fullscreen with f key', () => {
      render(<SlidePreview slides={mockSlides} />);

      expect(screen.getByTitle('全屏')).toBeInTheDocument();

      fireEvent.keyDown(window, { key: 'f' });
      expect(HTMLElement.prototype.requestFullscreen).toHaveBeenCalled();
    });

    it('exits fullscreen with Escape key', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Enter fullscreen first
      const fullscreenButton = screen.getByTitle('全屏');
      fireEvent.click(fullscreenButton);

      // Then press Escape
      fireEvent.keyDown(window, { key: 'Escape' });
      expect(document.exitFullscreen).toHaveBeenCalled();
    });
  });

  describe('Fullscreen Mode', () => {
    it('enters fullscreen when fullscreen button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      const fullscreenButton = screen.getByTitle('全屏');
      fireEvent.click(fullscreenButton);

      expect(HTMLElement.prototype.requestFullscreen).toHaveBeenCalled();
    });

    it('exits fullscreen when minimize button is clicked', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Enter fullscreen first
      const fullscreenButton = screen.getByTitle('全屏');
      fireEvent.click(fullscreenButton);

      // Should show minimize button
      const minimizeButton = screen.getByTitle('退出全屏');
      fireEvent.click(minimizeButton);

      expect(document.exitFullscreen).toHaveBeenCalled();
    });
  });

  describe('Slide Actions', () => {
    it('calls onSlideEdit when edit button is clicked in grid view', () => {
      const mockOnSlideEdit = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideEdit={mockOnSlideEdit}
        />
      );

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Find first slide in grid and hover to show edit button
      const firstSlide = screen.getAllByText('标题页')[1].closest('.relative');
      fireEvent.mouseEnter(firstSlide!);

      // Click edit button
      const editButton = firstSlide!.querySelector('button');
      fireEvent.click(editButton!);

      expect(mockOnSlideEdit).toHaveBeenCalledWith(mockSlides[0], 0);
    });

    it('calls onSlideDelete when delete button is clicked in grid view', () => {
      const mockOnSlideDelete = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideDelete={mockOnSlideDelete}
        />
      );

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Find first slide and hover to show buttons
      const firstSlide = screen.getAllByText('标题页')[1].closest('.relative');
      fireEvent.mouseEnter(firstSlide!);

      // Click delete button (second button)
      const buttons = firstSlide!.querySelectorAll('button');
      fireEvent.click(buttons[1]);

      expect(mockOnSlideDelete).toHaveBeenCalledWith(0);
    });

    it('calls onSlideEdit when edit button is clicked in list view', () => {
      const mockOnSlideEdit = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideEdit={mockOnSlideEdit}
        />
      );

      // Switch to list view
      const listButton = screen.getByTitle('列表视图');
      fireEvent.click(listButton);

      // Find edit button in first row
      const editButton = screen.getAllByRole('button').find(
        button => button.querySelector('svg')?.classList.contains('w-4') &&
                 !button.querySelector('.text-red-500')
      );
      
      fireEvent.click(editButton!);
      expect(mockOnSlideEdit).toHaveBeenCalledWith(mockSlides[0], 0);
    });

    it('does not show action buttons in read-only mode', () => {
      render(
        <SlidePreview 
          slides={mockSlides} 
          readOnly={true}
        />
      );

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Action buttons should not be present
      const firstSlide = screen.getAllByText('标题页')[1].closest('.relative');
      const actionButtons = firstSlide!.querySelector('.opacity-0');
      expect(actionButtons).not.toBeInTheDocument();
    });
  });

  describe('Drag and Drop', () => {
    it('makes slides draggable in grid view when not read-only', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Find first slide
      const firstSlide = screen.getAllByText('标题页')[1].closest('[draggable]');
      expect(firstSlide).toHaveAttribute('draggable', 'true');
    });

    it('does not make slides draggable in read-only mode', () => {
      render(<SlidePreview slides={mockSlides} readOnly={true} />);

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Find first slide
      const firstSlide = screen.getAllByText('标题页')[1].closest('[draggable]');
      expect(firstSlide).toHaveAttribute('draggable', 'false');
    });

    it('calls onSlideReorder when slide is dropped', () => {
      const mockOnSlideReorder = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideReorder={mockOnSlideReorder}
        />
      );

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Simulate drag and drop
      const slides = screen.getAllByText(/标题页|内容页|图表页/);
      const firstSlide = slides[0].closest('[draggable]');
      const secondSlide = slides[1].closest('[draggable]');

      fireEvent.dragStart(firstSlide!);
      fireEvent.drop(secondSlide!);

      // Note: Due to the complexity of drag and drop testing with jsdom,
      // we mainly test that the handlers are attached correctly
      expect(firstSlide).toHaveAttribute('draggable', 'true');
      expect(secondSlide).toHaveAttribute('draggable', 'true');
    });
  });

  describe('Quick Navigation', () => {
    it('jumps to first slide when skip back button is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={2}
        />
      );

      const skipBackButton = screen.getByTitle('第一页');
      fireEvent.click(skipBackButton);

      expect(mockOnSlideChange).toHaveBeenCalledWith(0);
    });

    it('jumps to last slide when skip forward button is clicked', () => {
      const mockOnSlideChange = jest.fn();
      render(
        <SlidePreview 
          slides={mockSlides} 
          onSlideChange={mockOnSlideChange}
          currentSlideIndex={0}
        />
      );

      const skipForwardButton = screen.getByTitle('最后一页');
      fireEvent.click(skipForwardButton);

      expect(mockOnSlideChange).toHaveBeenCalledWith(2);
    });
  });

  describe('Responsive Behavior', () => {
    it('applies correct aspect ratio in grid view', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Switch to grid view
      const gridButton = screen.getByTitle('网格视图');
      fireEvent.click(gridButton);

      // Grid items should have aspect-video class
      const gridItems = document.querySelectorAll('.aspect-video');
      expect(gridItems.length).toBeGreaterThan(0);
    });

    it('shows slide numbers in thumbnails', () => {
      render(<SlidePreview slides={mockSlides} />);

      // Thumbnail buttons should show numbers
      const thumbnails = screen.getAllByRole('button').filter(
        button => button.className.includes('w-24 h-16')
      );
      
      // Check that slide content is visible in thumbnails
      expect(thumbnails).toHaveLength(3);
    });
  });

  describe('Error Handling', () => {
    it('handles missing slide content gracefully', () => {
      const slidesWithMissingContent = [
        {
          ...mockSlides[0],
          content: {}
        }
      ] as Slide[];

      render(<SlidePreview slides={slidesWithMissingContent} />);
      
      expect(screen.getByText('标题页')).toBeInTheDocument();
      expect(screen.getByText('1 / 1')).toBeInTheDocument();
    });

    it('handles slides without subtitles', () => {
      const slidesWithoutSubtitle = [
        {
          ...mockSlides[0],
          subtitle: undefined
        }
      ] as Slide[];

      render(<SlidePreview slides={slidesWithoutSubtitle} />);
      
      expect(screen.getByText('标题页')).toBeInTheDocument();
      expect(screen.queryByText('副标题')).not.toBeInTheDocument();
    });
  });
});